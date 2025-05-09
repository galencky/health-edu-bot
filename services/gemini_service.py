import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def call_zh(prompt: str) -> str:
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction="""You are a medical education assistant. Respond in Traditional Chinese, plain text only."""
    )
    resp = model.generate_content(prompt, generation_config={"temperature": 0.25})
    return resp.text

def call_translate(zh_text: str, target_lang: str) -> str:
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction=f"You are a translation assistant. Translate to {target_lang}, plain text only."
    )
    resp = model.generate_content(zh_text, generation_config={"temperature": 0.25})
    return resp.text
