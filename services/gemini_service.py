import os
import google.generativeai as genai
from .prompt_config import zh_prompt, translate_prompt_template
# from google.generativeai import grounding  # Uncomment when you have grounding access

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def call_zh(prompt: str, system_prompt: str = zh_prompt) -> str:
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction=system_prompt,
        # tools=[grounding.GoogleSearch()]  # Enable later
    )
    resp = model.generate_content(prompt, generation_config={"temperature": 0.25})
    return resp.text

def call_translate(zh_text: str, target_lang: str) -> str:
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction=translate_prompt_template.format(lang=target_lang),
        # tools=[grounding.GoogleSearch()]  # Enable once paid plan allows grounding
    )
    resp = model.generate_content(zh_text, generation_config={"temperature": 0.25})
    return resp.text

def plainify(text: str) -> str:
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction=plainify_prompt,
    )
    return model.generate_content(text, generation_config={"temperature": 0.25}).text

def confirm_translate(plain_zh: str, target_lang: str) -> str:
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction=confirm_translate_prompt.format(lang=target_lang),
    )
    return model.generate_content(plain_zh, generation_config={"temperature": 0.2}).text
