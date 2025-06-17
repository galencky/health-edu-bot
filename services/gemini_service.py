"""
Gemini AI Service - Handles AI content generation, translation, and reference extraction
Provides thread-safe API calls with circuit breaker and rate limiting
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

# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

# API Configuration
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("❌ GEMINI_API_KEY not found in .env")

# Timeout and retry settings
API_TIMEOUT_SECONDS = 45  # Timeout for API calls
MAX_RETRIES = 2          # Number of retries on failure
RETRY_DELAY = 3          # Delay between retries (seconds)

# Model configuration
MODEL_NAME = "gemini-2.5-flash-preview-05-20"
DEFAULT_TEMPERATURE = 0.25

# ============================================================
# INITIALIZATION
# ============================================================

# Shared API client
_client = genai.Client(api_key=API_KEY)
_tools = [types.Tool(google_search=types.GoogleSearch())]

# Thread pool for async execution
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='gemini')

# Thread-safe storage for last API response (for reference extraction)
_last_response_lock = threading.Lock()
_last_response = None

# ============================================================
# CORE API FUNCTIONS
# ============================================================

def _build_api_config(
    user_text: str,
    system_prompt: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE
) -> types.GenerateContentConfig:
    """
    Build API configuration for Gemini call
    
    Args:
        user_text: User input text
        system_prompt: Optional system instruction
        temperature: Model temperature (0-1)
        
    Returns:
        GenerateContentConfig object
    """
    # Build system instructions
    system_instructions = []
    if system_prompt:
        system_instructions.append(types.Part.from_text(text=system_prompt))
    
    # Create configuration
    return types.GenerateContentConfig(
        temperature=temperature,
        tools=_tools,
        response_mime_type="text/plain",
        system_instruction=system_instructions
    )


def _make_api_call_with_retry(contents, config) -> Optional[object]:
    """
    Make API call with retry logic
    
    Returns API response or raises exception after retries
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            # Submit to thread pool with timeout
            future = _executor.submit(
                _client.models.generate_content,
                model=MODEL_NAME,
                contents=contents,
                config=config,
            )
            response = future.result(timeout=API_TIMEOUT_SECONDS)
            
            # Store response for reference extraction
            with _last_response_lock:
                global _last_response
                _last_response = response
            
            return response
            
        except TimeoutError:
            if attempt < MAX_RETRIES:
                print(f"[GEMINI] Timeout on attempt {attempt + 1}, retrying...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                raise TimeoutError(
                    f"API timeout after {API_TIMEOUT_SECONDS}s "
                    f"({MAX_RETRIES + 1} attempts)"
                )
        
        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"[GEMINI] Error on attempt {attempt + 1}: {e}, retrying...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                raise


def _call_genai(
    user_text: str,
    sys_prompt: Optional[str] = None,
    temp: float = DEFAULT_TEMPERATURE
) -> str:
    """
    Internal function to call Gemini API
    
    Features:
    - Thread-safe API calls
    - Automatic retry on failure
    - Circuit breaker protection
    - Response storage for reference extraction
    
    Args:
        user_text: User input text
        sys_prompt: Optional system prompt
        temp: Model temperature
        
    Returns:
        Generated text response or error message
    """
    # Build request content
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_text)],
        ),
    ]
    
    # Build configuration
    config = _build_api_config(user_text, sys_prompt, temp)
    
    # Make API call with circuit breaker protection
    try:
        response = gemini_circuit_breaker.call(
            lambda: _make_api_call_with_retry(contents, config)
        )
        
    except CircuitBreakerError as e:
        print(f"🚫 [GEMINI] Circuit breaker open: {e}")
        return "⚠️ AI 服務暫時過載，請稍等片刻後再試。系統正在自動恢復中。"
        
    except TimeoutError as e:
        print(f"⏱️ [GEMINI] Timeout: {e}")
        return "⚠️ AI 服務響應超時，請稍後再試。"
        
    except Exception as e:
        print(f"❌ [GEMINI] API call failed: {e}")
        return "⚠️ AI 服務暫時無法使用，請稍後再試。"
    
    # Extract text from response
    try:
        if response and response.candidates and response.candidates[0].content.parts:
            return response.candidates[0].content.parts[0].text
        return ""
    except Exception as e:
        print(f"[GEMINI] Error extracting response text: {e}")
        return ""

# ============================================================
# PUBLIC API FUNCTIONS
# ============================================================

@rate_limit(gemini_limiter, key_func=lambda *args, **kwargs: "global")
def call_zh(prompt: str, system_prompt: str = zh_prompt) -> str:
    """
    Generate Chinese health education content
    
    Args:
        prompt: User query or topic
        system_prompt: System instruction (defaults to zh_prompt)
        
    Returns:
        Generated Chinese content
    """
    return _call_genai(prompt, sys_prompt=system_prompt, temp=DEFAULT_TEMPERATURE)


@rate_limit(gemini_limiter, key_func=lambda *args, **kwargs: "global")
def call_translate(zh_text: str, target_lang: str) -> str:
    """
    Translate Chinese text to target language
    
    Args:
        zh_text: Chinese text to translate
        target_lang: Target language name
        
    Returns:
        Translated text
    """
    sys_prompt = translate_prompt_template.format(lang=target_lang)
    return _call_genai(zh_text, sys_prompt=sys_prompt, temp=DEFAULT_TEMPERATURE)


@rate_limit(gemini_limiter, key_func=lambda *args, **kwargs: "global")
def plainify(text: str) -> str:
    """
    Simplify text to plain language
    
    Args:
        text: Text to simplify
        
    Returns:
        Simplified text
    """
    return _call_genai(text, sys_prompt=plainify_prompt, temp=DEFAULT_TEMPERATURE)


@rate_limit(gemini_limiter, key_func=lambda *args, **kwargs: "global")
def confirm_translate(plain_zh: str, target_lang: str) -> str:
    """
    Translate simplified Chinese text with confirmation
    
    Args:
        plain_zh: Simplified Chinese text
        target_lang: Target language name
        
    Returns:
        Confirmed translation
    """
    sys_prompt = confirm_translate_prompt.format(lang=target_lang)
    return _call_genai(plain_zh, sys_prompt=sys_prompt, temp=0.2)  # Lower temp for accuracy


# ============================================================
# REFERENCE EXTRACTION
# ============================================================

def get_references() -> List[Dict[str, str]]:
    """
    Extract references from the last Gemini API response
    
    Must be called immediately after any Gemini API call to get references
    from that specific response.
    
    Returns:
        List of reference dictionaries with 'title' and 'url' keys
        Always returns a list (empty if no references found)
    """
    try:
        # Get last response with thread safety
        with _last_response_lock:
            last_response = _last_response
        
        if not last_response:
            return []
        
        # Safely check for candidates
        if not last_response.candidates or len(last_response.candidates) == 0:
            return []
        
        # Extract grounding metadata
        candidate = last_response.candidates[0]
        grounding = getattr(candidate, "grounding_metadata", None)
        
        if not grounding:
            return []
        
        # Check for search entry point
        search_entry = getattr(grounding, "search_entry_point", None)
        if not search_entry:
            return []
        
        # Get rendered content
        rendered_content = getattr(search_entry, "rendered_content", None)
        if not rendered_content:
            return []
        
        # Parse HTML for references
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


def references_to_flex(
    refs: List[Dict[str, str]], 
    headline: str = "參考來源"
) -> Optional[Dict]:
    """
    Convert references to LINE Flex Message format
    
    Args:
        refs: List of reference dictionaries
        headline: Header text for the reference section
        
    Returns:
        Flex message dictionary or None if no references
    """
    if not refs:
        return None
    
    # Build content items
    contents = [
        {
            "type": "text",
            "text": headline,
            "weight": "bold",
            "size": "lg",
            "margin": "md"
        }
    ]
    
    # Add each reference as a clickable link
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
    
    # Build flex message structure
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": contents
        }
    }
