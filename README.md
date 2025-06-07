# MedEdBot – FastAPI + LINE Chatbot with Google Gemini Integration

**Author:** Kuan-Yuan Chen, M.D.  
**Contact:** galen147258369@gmail.com  

---

## 🚀 Project Overview

MedEdBot is a multilingual health-education and real-time translation chatbot built with FastAPI, LINE Messaging API, and Google’s Gemini AI models. It supports:

- **Health Education Sheets (“衛教”)**  
  Generate structured Traditional Chinese patient-education sheets (「衛教單張」), edit, translate into various languages, and email or deliver via LINE.
- **MedChat Translation**  
  Real-time conversational translation between Chinese and a user-selected language, with optional AI-generated text-to-speech.
- **Voicemail Transcription & Translation**  
  Upload LINE voice messages, transcribe via Gemini STT, then translate on demand.
- **Text-to-Speech (TTS)**  
  AI-generated TTS audio delivered in-chat or logged to Google Drive & Sheets.
- **Logging & Analytics**  
  All interactions (text, audio, Gemini logs) are archived to Google Drive and Google Sheets for audit and analysis.

---

## 📂 Repository Structure

~~~

.
├── main.py                   # FastAPI app entrypoint
├── routes/
│   └── webhook.py            # LINE webhook endpoint & handlers registration
├── handlers/
│   ├── line\_handler.py       # LINE event handlers (text & audio)
│   ├── logic\_handler.py      # Core dispatcher for modes & commands
│   ├── session\_manager.py    # In-memory session store per user
│   ├── medchat\_handler.py    # Real-time chat translation logic
│   └── mail\_handler.py       # Email sending logic for health-education sheets
├── services/
│   ├── gemini\_service.py     # Wrapper for Google Gemini API calls
│   ├── prompt\_config.py      # System prompts & templates
│   ├── stt\_service.py        # Gemini-based speech-to-text
│   └── tts\_service.py        # Gemini-based text-to-speech
├── utils/
│   ├── command\_sets.py       # Recognized command keywords
│   ├── email\_service.py      # SMTP email helper
│   ├── google\_drive\_service.py  # Google Drive upload helper
│   ├── google\_sheets.py      # Google Sheets helper
│   ├── log\_to\_sheets.py      # Append interaction logs to Sheets
│   ├── tts\_log.py            # Background TTS Drive & Sheets logger
│   └── voicemail\_drive.py    # Upload voicemail files to Drive
├── tts\_audio/                # Local storage for generated WAV files
├── voicemail/                # Downloaded LINE voice-message files
├── .env                      # Environment variables (not in repo)
└── requirements.txt          # Python dependencies

~~~

---

## 🔧 Prerequisites

- Python 3.9+  
- A LINE Messaging API channel (access token & secret)  
- Google Cloud Service Account JSON (base64-encoded in `GOOGLE_CREDS_B64`)  
- Gmail account & app-specific password  
- Google Drive folder ID for logs & audio  
- A publicly accessible `BASE_URL` pointing to your server (for TTS audio URLs)  

---

## ⚙️ Configuration

Create a `.env` file in project root with the following variables:

~~~
-LINE
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret

-Gemini API
GEMINI_API_KEY=your_google_gemini_api_key

-SMTP Email (Gmail)
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password

-Google Drive & Sheets
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
GOOGLE_CREDS_B64=base64_encoded_service_account_json

-Server URL (for TTS)
BASE_URL=https://your.domain.com
~~~

---

## 📥 Installation

1. Clone the repository:

   ~~~
   git clone https://github.com/your-org/mededbot.git
   cd mededbot
   ~~~

2. Install dependencies:

   ~~~
   pip install -r requirements.txt
   ~~~

3. Create and populate your `.env` (see above).

---

## 🏃 Running Locally

~~~
uvicorn main:app --host 0.0.0.0 --port 10000 --reload
~~~

* **Static TTS audio** will be served at `http://localhost:10000/static/<filename>.wav`.
* **LINE webhook endpoint**: `POST /webhook`
* **Test chat endpoint**: `POST /chat`

~~~
  { "message": "你好" }
~~~

---

## 📍 API Endpoints

| Path       | Method   | Description                                |
| ---------- | -------- | ------------------------------------------ |
| `/`        | GET      | Health check & list of available endpoints |
| `/ping`    | GET/HEAD | Simple JSON status `"ok"`                  |
| `/chat`    | POST     | Simple testing endpoint (bypasses LINE)    |
| `/webhook` | POST     | LINE webhook for text & audio events       |

---

## 💬 Usage & Commands

1. **Start a new session**
   Send `new` or `開始`
2. **Choose mode**

   * Enter `ed` / `education` / `衛教` → Health-education sheet
   * Enter `chat` / `聊天` → Real-time MedChat
3. **In “衛教” mode**

   * Send `<疾病名稱> <衛教主題>` → Generate Chinese sheet
   * `modify` / `修改` → Edit generated sheet
   * `translate` / `翻譯` → Translate to your target language
   * `mail` / `寄送` → Email the content
   * `speak` / `朗讀` → (Only after translation) Generate TTS
4. **In “聊天” mode**

   * First send target language (e.g. `英文`)
   * Then send any text → Gemini will plainify & translate
   * `speak` / `朗讀` → Generate TTS of last translation
5. **Voicemail**

   * Send an audio message → Bot replies with transcription
   * Reply with `<lang>` or `new`/`無` → Bot translates or cancels

---

## 🔍 Logging & Auditing

* **Text logs** are uploaded as `.txt` files to Google Drive and linked in Google Sheets (`ChatbotLogs`).
* **TTS audio** files are saved locally under `tts_audio/`, uploaded to Drive, and logged in `TTSLogs` sheet.
* **Voicemail uploads** are stored under `voicemail/` and backed up to Drive.

---

## 🛠️ Extending & Customizing

* **Prompts**
  Modify system prompts in `services/prompt_config.py` to tailor GPT behavior.
* **Commands**
  Edit `utils/command_sets.py` to add synonyms or new commands.
* **Session Storage**
  Replace in-memory `handlers/session_manager.py` with Redis or database for persistence.
* **Deployment**
  Containerize with Docker, expose `/static` and `/webhook` via HTTPS, and configure LINE webhook URL accordingly.

---

## 📜 License

This project is released under the MIT License.

---

*Thank you for using MedEdBot!*
— Kuan-Yuan Chen, M.D. (陳冠元 醫師)
[galen147258369@gmail.com](mailto:galen147258369@gmail.com)

