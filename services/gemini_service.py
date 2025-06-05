import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from .prompt_config import zh_prompt, translate_prompt_template, plainify_prompt, confirm_translate_prompt

# ---- Load API key from .env ----
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ GEMINI_API_KEY not found in .env")

# ---- Shared Gemini API client ----
_client = genai.Client(api_key=api_key)
_model = "gemini-2.5-flash-preview-05-20"
_tools = [types.Tool(google_search=types.GoogleSearch())]  # Uncomment to enable Search grounding

def _call_genai(user_text, sys_prompt=None, temp=0.25):
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_text)],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=temp,
        tools=_tools,  # Uncomment to enable Search grounding
        response_mime_type="text/plain",
        system_instruction=[
            types.Part.from_text(text=sys_prompt) if sys_prompt else None,
        ],
    )
    # Remove None in system_instruction for safety
    generate_content_config.system_instruction = [
        part for part in generate_content_config.system_instruction if part is not None
    ]
    response = _client.models.generate_content(
        model=_model,
        contents=contents,
        config=generate_content_config,
    )
    # Standard output handling as before
    return response.candidates[0].content.parts[0].text if response.candidates[0].content.parts else ""

def call_zh(prompt: str, system_prompt: str = zh_prompt) -> str:
    return _call_genai(prompt, sys_prompt=system_prompt, temp=0.25)

def call_translate(zh_text: str, target_lang: str) -> str:
    sys_prompt = translate_prompt_template.format(lang=target_lang)
    return _call_genai(zh_text, sys_prompt=sys_prompt, temp=0.25)

def plainify(text: str) -> str:
    return _call_genai(text, sys_prompt=plainify_prompt, temp=0.25)

def confirm_translate(plain_zh: str, target_lang: str) -> str:
    sys_prompt = confirm_translate_prompt.format(lang=target_lang)
    return _call_genai(plain_zh, sys_prompt=sys_prompt, temp=0.2)
