# Mededbot-多語言衛教AI 🤖🇹🇼

A FastAPI-powered LINE chatbot that generates and translates medical education content using the Gemini API. It supports multilingual output, email delivery, Google Sheets logging, and Google Drive backup — tailored for health professionals in Taiwan and beyond.

---

## 🚀 Features

- 🧠 Gemini API integration for zh-TW health education generation
- 🌐 Multilingual translation support (user-defined target language)
- 📩 Gmail SMTP support to email translated leaflets
- 📊 Google Sheets logging for audit and analysis
- ☁️ Google Drive backups for Gemini-generated content
- 💬 LINE Messaging API integration with real-time response
- ✅ Supports multiple concurrent users with session isolation

---

## 🧰 Tech Stack

- Python 3.10+
- FastAPI
- LINE Messaging API SDK
- Google Generative AI (`google.generativeai`)
- Google Drive + Sheets API via `gspread` + `google-api-python-client`
- SMTP (`smtplib`) with Gmail App Password
- Render (for deployment)

---

## 🗂️ Project Structure

```

health-edu-bot/
├── main.py                     # FastAPI app entrypoint
├── handlers/
│   ├── line_handler.py         # Handles LINE messaging events
│   ├── logic_handler.py        # Handles session + command logic
│   └── mail_handler.py         # Handles email composition and sending
├── services/
│   └── gemini_service.py       # Gemini API logic (generation, translation)
├── utils/
│   ├── email_service.py        # SMTP email utility
│   ├── log_to_sheets.py        # Google Sheets + Drive logging
│   └── google_drive_service.py # Google Drive uploader
├── .env.example                # Sample environment config
├── requirements.txt            # Python dependencies
└── README.md                   # You're reading it!

````

---

## 🛠️ Setup & Configuration

### 1. Clone the repo

```bash
git clone https://github.com/galencky/health-edu-bot.git
cd health-edu-bot
````

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up `.env` file

Copy `.env.example` to `.env` and fill in your credentials:

```env
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_CHANNEL_SECRET=...
GEMINI_API_KEY=...

GMAIL_ADDRESS=youraddress@gmail.com
GMAIL_APP_PASSWORD=your16charapppassword

GOOGLE_CREDS_B64=...  # Base64-encoded Google service account key
GDRIVE_FOLDER_ID=...  # Folder ID to upload .txt files
```

> 💡 Use [Google App Passwords](https://myaccount.google.com/apppasswords) and remove spaces before placing in `.env`

---

## 🧪 Local Testing

```bash
uvicorn main:app --reload
```

Use tools like `ngrok` to tunnel `POST /webhook` to your local FastAPI app for LINE callback testing.

---

## 🚀 Deployment to Render

1. Push your code to GitHub
2. Create a new **Web Service** on [Render](https://render.com/)
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn main:app --host 0.0.0.0 --port 10000`
5. Add environment variables via the Render dashboard
6. Deploy and connect to your LINE webhook

---

## 📷 User Flow

1. User types: `new` to start
2. Enters `疾病名稱 + 衛教主題`
3. Bot generates Gemini-based zh-TW content
4. User can:

   * `modify` → provide zh-TW modification instructions
   * `translate` → specify translation language
   * `mail` → provide email address to send the final content
5. The system logs interactions to Google Sheets and backs up the output to Google Drive

---

## 📄 License

MIT License. See `LICENSE` file for details.

---

## 🙌 Maintainer

Developed by [陳冠元 Galen Chen, M.D.](mailto:galen147258369@gmail.com)

If you found this project helpful, feel free to ⭐️ star the repo or reach out with ideas!