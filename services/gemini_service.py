from dotenv import load_dotenv
load_dotenv()

import os
from google import genai
from google.genai import types

from bs4 import BeautifulSoup
from .prompt_config import zh_prompt, translate_prompt_template, plainify_prompt, confirm_translate_prompt

# ---- Load API key from .env ----

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ GEMINI_API_KEY not found in .env")

# ---- Shared Gemini API client ----
_client = genai.Client(api_key=api_key)
_model = "gemini-2.5-flash-preview-05-20"
_tools = [types.Tool(google_search=types.GoogleSearch())]

# Store last response globally (thread safe for single request model)
_last_response = None

def _call_genai(user_text, sys_prompt=None, temp=0.25):
    """
    Internal function to call Gemini, store response for reference extraction.
    Returns only the answer string.
    """
    global _last_response
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_text)],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=temp,
        tools=_tools,
        response_mime_type="text/plain",
        system_instruction=[
            types.Part.from_text(text=sys_prompt) if sys_prompt else None,
        ],
    )
    # Remove None in system_instruction for safety
    generate_content_config.system_instruction = [
        part for part in generate_content_config.system_instruction if part is not None
    ]
    _last_response = _client.models.generate_content(
        model=_model,
        contents=contents,
        config=generate_content_config,
    )
    # Standard output: answer as text string
    return _last_response.candidates[0].content.parts[0].text if _last_response.candidates[0].content.parts else ""

def call_zh(prompt: str, system_prompt: str = zh_prompt) -> str:
    """Call Gemini with zh_prompt, return answer string."""
    return _call_genai(prompt, sys_prompt=system_prompt, temp=0.25)

def call_translate(zh_text: str, target_lang: str) -> str:
    """Call Gemini to translate, return answer string."""
    sys_prompt = translate_prompt_template.format(lang=target_lang)
    return _call_genai(zh_text, sys_prompt=sys_prompt, temp=0.25)

def plainify(text: str) -> str:
    """Call Gemini to plainify text, return answer string."""
    return _call_genai(text, sys_prompt=plainify_prompt, temp=0.25)

def confirm_translate(plain_zh: str, target_lang: str) -> str:
    """Call Gemini to translate and confirm, return answer string."""
    sys_prompt = confirm_translate_prompt.format(lang=target_lang)
    return _call_genai(plain_zh, sys_prompt=sys_prompt, temp=0.2)

def get_references():
    """
    Call immediately after call_zh/call_translate/plainify/confirm_translate.
    Returns a list of dicts: [{title:..., url:...}, ...]
    If no references found, returns empty list.
    """
    global _last_response
    if not _last_response:
        return []
    grounding = getattr(_last_response.candidates[0], "grounding_metadata", None)
    refs = []
    if (
        grounding
        and hasattr(grounding, "search_entry_point")
        and getattr(grounding.search_entry_point, "rendered_content", None)
    ):
        rendered_html = grounding.search_entry_point.rendered_content
        soup = BeautifulSoup(rendered_html, "html.parser")
        refs = [
            {"title": a.text.strip(), "url": a["href"]}
            for a in soup.find_all("a", class_="chip")
        ]
    return refs

def references_to_flex(refs, headline="參考來源"):
    """
    Convert references list to a LINE Flex Message (JSON) for clickable links.
    """
    if not refs:
        return None
    flex_contents = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": (
                [{"type": "text", "text": headline, "weight": "bold", "size": "lg", "margin": "md"}] +
                [
                    {
                        "type": "text",
                        "text": r["title"],
                        "size": "md",
                        "color": "#3366CC",
                        "action": {"type": "uri", "uri": r["url"]},
                        "margin": "md",
                        "wrap": True
                    }
                    for r in refs
                ]
            )
        }
    }
    return flex_contents
