"""
Gemini AI Service
"""
import os
import time
import threading
from concurrent.futures import TimeoutError, ThreadPoolExecutor
from typing import List, Dict, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from bs4 import BeautifulSoup

from .prompt_config import (
    zh_prompt, translate_prompt_template, 
    plainify_prompt, confirm_translate_prompt
)
from utils.rate_limiter import rate_limit, gemini_limiter
from utils.circuit_breaker import gemini_circuit_breaker, CircuitBreakerError

load_dotenv()

# Configuration
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found in .env")

API_TIMEOUT_SECONDS = 45
MAX_RETRIES = 2
RETRY_DELAY = 3
MODEL_NAME = "gemini-2.5-flash"

# Shared resources
_client = genai.Client(api_key=API_KEY)
_tools = [types.Tool(google_search=types.GoogleSearch())]
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='gemini')
_last_response_lock = threading.Lock()
_last_response = None

def _call_genai(user_text: str, sys_prompt: Optional[str] = None, temp: float = 0.25) -> str:
    """Internal function to call Gemini API"""
    # Build request
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_text)],
        ),
    ]
    
    # Build config
    system_instructions = []
    if sys_prompt:
        system_instructions.append(types.Part.from_text(text=sys_prompt))
    
    config = types.GenerateContentConfig(
        temperature=temp,
        max_output_tokens=2000,
        tools=_tools,
        response_mime_type="text/plain",
        system_instruction=system_instructions
    )
    
    # Make API call with retries
    for attempt in range(MAX_RETRIES + 1):
        try:
            # Call with circuit breaker
            def api_call():
                future = _executor.submit(
                    _client.models.generate_content,
                    model=MODEL_NAME,
                    contents=contents,
                    config=config,
                )
                response = future.result(timeout=API_TIMEOUT_SECONDS)
                
                # Store response
                with _last_response_lock:
                    global _last_response
                    _last_response = response
                
                return response
            
            response = gemini_circuit_breaker.call(api_call)
            
            # Extract text
            if response and response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            return ""
            
        except CircuitBreakerError:
            return "⚠️ AI 服務暫時過載，請稍等片刻後再試。"
        except TimeoutError:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
            return "⚠️ AI 服務響應超時，請稍後再試。"
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
            print(f"[GEMINI] API error: {e}")
            return "⚠️ AI 服務暫時無法使用，請稍後再試。"
    
    return "⚠️ AI 服務暫時無法使用，請稍後再試。"

@rate_limit(gemini_limiter, key_func=lambda *args, **kwargs: "global")
def call_zh(prompt: str, system_prompt: str = zh_prompt) -> str:
    """Generate Chinese health education content"""
    return _call_genai(prompt, sys_prompt=system_prompt, temp=0.25)

@rate_limit(gemini_limiter, key_func=lambda *args, **kwargs: "global")
def call_translate(zh_text: str, target_lang: str) -> str:
    """Translate Chinese text to target language"""
    sys_prompt = translate_prompt_template.format(lang=target_lang)
    return _call_genai(zh_text, sys_prompt=sys_prompt, temp=0.25)

@rate_limit(gemini_limiter, key_func=lambda *args, **kwargs: "global")
def plainify(text: str) -> str:
    """Simplify text to plain language"""
    return _call_genai(text, sys_prompt=plainify_prompt, temp=0.25)

@rate_limit(gemini_limiter, key_func=lambda *args, **kwargs: "global")
def confirm_translate(plain_zh: str, target_lang: str) -> str:
    """Translate simplified Chinese text"""
    sys_prompt = confirm_translate_prompt.format(lang=target_lang)
    return _call_genai(plain_zh, sys_prompt=sys_prompt, temp=0.2)

def get_references() -> List[Dict[str, str]]:
    """Extract references from last Gemini response"""
    try:
        with _last_response_lock:
            last_response = _last_response
        
        if not last_response or not last_response.candidates:
            return []
        
        candidate = last_response.candidates[0]
        grounding = getattr(candidate, "grounding_metadata", None)
        if not grounding:
            return []
        
        search_entry = getattr(grounding, "search_entry_point", None)
        if not search_entry:
            return []
        
        rendered_content = getattr(search_entry, "rendered_content", None)
        if not rendered_content:
            return []
        
        # Parse HTML
        soup = BeautifulSoup(rendered_content, "html.parser")
        references = []
        
        for link in soup.find_all("a", class_="chip"):
            if link.text and link.get("href"):
                references.append({
                    "title": link.text.strip(),
                    "url": link["href"]
                })
        
        return references
        
    except Exception as e:
        print(f"[GEMINI] Error extracting references: {e}")
        return []

def references_to_flex(refs: List[Dict[str, str]], headline: str = "參考來源") -> Optional[Dict]:
    """Convert references to LINE Flex Message format"""
    if not refs:
        return None
    
    contents = [
        {
            "type": "text",
            "text": headline,
            "weight": "bold",
            "size": "lg",
            "margin": "md"
        }
    ]
    
    for ref in refs:
        contents.append({
            "type": "text",
            "text": ref["title"],
            "size": "md",
            "color": "#3366CC",
            "action": {
                "type": "uri",
                "uri": ref["url"]
            },
            "margin": "md",
            "wrap": True
        })
    
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": contents
        }
    }