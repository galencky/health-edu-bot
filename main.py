from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

app = FastAPI()

# Basic state (1 global session for test)
session = {
    "language": None,
    "disease": None,
    "topic": None,
    "last_prompt": None,
    "last_response": None,
}

class UserInput(BaseModel):
    message: str

def build_prompt(language, disease, topic):
    return (
        f"Please create a short, clear patient education pamphlet in two parts:\n\n"
        f"1. English version\n"
        f"2. Translated version in {language}\n\n"
        f"Topic: {disease} — {topic}\n\n"
        f"The goal is to help clinicians educate patients or caregivers in their native language during a clinic visit."
    )

def call_gemini(prompt):
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction="You are a medical education assistant. First respond in English, then translate into the requested language. Do not reference websites."
    )
    stream = model.generate_content(prompt, stream=True)
    return "".join(chunk.text or "" for chunk in stream)

@app.post("/chat")
def chat(input: UserInput):
    global session
    text = input.message.strip().lower()

    if "new" in text:
        session = {key: None for key in session}
        return {"reply": "🆕 New chat started."}

    elif "modify" in text and session["last_response"]:
        updated = text.replace("modify", "").strip()
        mod_prompt = f"Please revise this response based on the following request:\n\nRequest: {updated}\n\nOriginal:\n{session['last_response']}"
        result = call_gemini(mod_prompt)
        session["last_prompt"] = mod_prompt
        session["last_response"] = result
        return {"reply": result}

    elif "mail" in text:
        return {"reply": "📧 Mail feature not yet implemented in this version."}

    if not session["language"]:
        session["language"] = text
        return {"reply": "🌐 Language set. Please enter disease:"}
    elif not session["disease"]:
        session["disease"] = text
        return {"reply": "🩺 Disease set. Please enter health education topic:"}
    elif not session["topic"]:
        session["topic"] = text
        session["last_prompt"] = build_prompt(session["language"], session["disease"], session["topic"])
        session["last_response"] = call_gemini(session["last_prompt"])
        return {"reply": session["last_response"]}
    else:
        return {"reply": "✅ Prompt complete. You can type 'modify', 'mail', or 'new'."}
