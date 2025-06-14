from dotenv import load_dotenv
load_dotenv()

import os
from google import genai
from google.genai import types
import asyncio
from concurrent.futures import TimeoutError
import time
import threading

from bs4 import BeautifulSoup
from .prompt_config import zh_prompt, translate_prompt_template, plainify_prompt, confirm_translate_prompt
from utils.rate_limiter import rate_limit, gemini_limiter, RateLimitExceeded

# BUG FIX: Add timeout configuration for API calls with retry mechanism
# Previously: No timeout, requests could hang indefinitely
API_TIMEOUT_SECONDS = 50  # 50 second timeout for Gemini API calls
MAX_RETRIES = 1  # Retry once on timeout
RETRY_DELAY = 5  # 5 second delay between retries

# ---- Load API key from .env ----

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ GEMINI_API_KEY not found in .env")

# ---- Shared Gemini API client ----
_client = genai.Client(api_key=api_key)
_model = "gemini-2.5-flash-preview-05-20"
_tools = [types.Tool(google_search=types.GoogleSearch())]

# Thread-local storage for last response to prevent race conditions
_thread_local = threading.local()

def _call_genai(user_text, sys_prompt=None, temp=0.25):
    """
    Internal function to call Gemini, store response for reference extraction.
    Returns only the answer string.
    BUG FIX: Added timeout to prevent hanging requests
    BUG FIX: Use thread-local storage to prevent race conditions
    """
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
    
    # BUG FIX: Wrap API call with timeout and retry mechanism
    # Previously: Could hang indefinitely, no retries
    import concurrent.futures
    
    for attempt in range(MAX_RETRIES + 1):
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    _client.models.generate_content,
                    model=_model,
                    contents=contents,
                    config=generate_content_config,
                )
                response = future.result(timeout=API_TIMEOUT_SECONDS)
                # Store in thread-local storage to prevent race conditions
                _thread_local.last_response = response
                break  # Success, exit retry loop
        except concurrent.futures.TimeoutError:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
            else:
                raise TimeoutError(f"Gemini API call timed out after {API_TIMEOUT_SECONDS} seconds (tried {MAX_RETRIES + 1} times)")
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY) 
                continue
            else:
                raise Exception(f"Gemini API error: {str(e)}")
    
    # Standard output: answer as text string
    response = getattr(_thread_local, 'last_response', None)
    if response and response.candidates and response.candidates[0].content.parts:
        return response.candidates[0].content.parts[0].text
    return ""

@rate_limit(gemini_limiter, key_func=lambda *args, **kwargs: "global")  # Global rate limit
def call_zh(prompt: str, system_prompt: str = zh_prompt) -> str:
    """Call Gemini with zh_prompt, return answer string."""
    return _call_genai(prompt, sys_prompt=system_prompt, temp=0.25)

@rate_limit(gemini_limiter, key_func=lambda *args, **kwargs: "global")
def call_translate(zh_text: str, target_lang: str) -> str:
    """Call Gemini to translate, return answer string."""
    sys_prompt = translate_prompt_template.format(lang=target_lang)
    return _call_genai(zh_text, sys_prompt=sys_prompt, temp=0.25)

@rate_limit(gemini_limiter, key_func=lambda *args, **kwargs: "global")
def plainify(text: str) -> str:
    """Call Gemini to plainify text, return answer string."""
    return _call_genai(text, sys_prompt=plainify_prompt, temp=0.25)

@rate_limit(gemini_limiter, key_func=lambda *args, **kwargs: "global")
def confirm_translate(plain_zh: str, target_lang: str) -> str:
    """Call Gemini to translate and confirm, return answer string."""
    sys_prompt = confirm_translate_prompt.format(lang=target_lang)
    return _call_genai(plain_zh, sys_prompt=sys_prompt, temp=0.2)

def get_references():
    """
    Call immediately after call_zh/call_translate/plainify/confirm_translate.
    Returns a list of dicts: [{title:..., url:...}, ...]
    If no references found, returns empty list.
    BUG FIX: Use thread-local storage to prevent race conditions
    """
    last_response = getattr(_thread_local, 'last_response', None)
    if not last_response:
        return []
    grounding = getattr(last_response.candidates[0], "grounding_metadata", None)
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
