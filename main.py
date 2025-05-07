from fastapi import FastAPI
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variable
load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# FastAPI app
app = FastAPI()

# Global session state for simple demo
session = {
    "language": None,
    "disease": None,
    "topic": None,
    "last_prompt": None,
    "last_response": None,
}

# Input format for POST /chat
class UserInput(BaseModel):
    message: str

# Build prompt from session
def build_prompt(language, disease, topic):
    return (
        f"Please create a short, clear patient education pamphlet in two parts:\n\n"
        f"1. English version\n"
        f"2. Translated version in {language}\n\n"
        f"Topic: {disease} — {topic}\n\n"
        f"The goal is to help clinicians educate patients or caregivers in their native language during a clinic visit."
    )

# Call Gemini without stream
def call_gemini(prompt):
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-04-17",
        system_instruction="You are a medical education assistant. First respond in English, then translate into the requested language. Do not reference websites."
    )
    response = model.generate_content(prompt)
    return response.text

# POST /chat endpoint
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
        return {"reply": "📧 Mail feature not implemented yet."}

    # Sequential session handling
    if not session["language"]:
        session["language"] = input.message
        return {"reply": "🌐 Language set. Please enter disease:"}
    elif not session["disease"]:
        session["disease"] = input.message
        return {"reply": "🩺 Disease set. Please enter health education topic:"}
    elif not session["topic"]:
        session["topic"] = input.message
        session["last_prompt"] = build_prompt(session["language"], session["disease"], session["topic"])
        session["last_response"] = call_gemini(session["last_prompt"])
        return {"reply": session["last_response"]}
    else:
        return {"reply": "✅ Prompt complete. You can type 'modify', 'mail', or 'new'."}

# Optional: Add GET /
@app.get("/")
def root():
    return {"message": "✅ FastAPI is running. Try POST /chat with a message like 'thai'"}
