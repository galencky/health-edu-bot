# Mededbot - 多語言衛教 AI Chatbot

A multilingual health education chatbot built with **FastAPI**, integrated with **LINE Messaging API** and **Google Gemini API**, supporting dynamic patient education content generation, translation, email delivery, and logging to Google Sheets and Drive.

---

## 🚀 Features

* ✅ LINE-compatible multilingual chatbot interface
* ✅ Gemini API integration for generating 保健 content in Traditional Chinese (zh-TW)
* ✅ One-click modification, translation, and emailing of content
* ✅ Email validation with MX record checking
* ✅ Logging interaction data to Google Sheets and Gemini output to Google Drive
* ✅ Modular, scalable architecture

---

## 🌐 Demo Endpoints

| Endpoint   | Description                           |
| ---------- | ------------------------------------- |
| `/`        | Health check + basic endpoint info    |
| `/chat`    | Chatbot testing without LINE frontend |
| `/ping`    | Health check for uptime monitoring    |
| `/webhook` | LINE webhook receiver                 |

---

## 🚪 Setup & Installation

### 1. Clone and prepare environment

```bash
git clone https://github.com/YOUR_NAME/mededbot.git
cd mededbot
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. .env Configuration

Create a `.env` file with:

```env
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_CHANNEL_SECRET=...
GEMINI_API_KEY=...
GMAIL_ADDRESS=...
GMAIL_APP_PASSWORD=...
GOOGLE_CREDS_B64=...  # base64 encoded credentials.json
GOOGLE_DRIVE_FOLDER_ID=...  # folder ID for Gemini logs
```

---

## 🤖 How It Works

### ⚡ User Flow (via LINE)

1. **Start**: User enters `new` to initiate a session
2. **Input Topic**: User enters health topic
3. **Gemini** generates Traditional Chinese material
4. **Modify**: Optional user adjustments via `modify`
5. **Translate**: Optional translation via `translate`
6. **Mail**: Sends content via `mail`

### 📁 Core Modules and Their Responsibilities

| File / Module                   | Responsibility                                                                 |
| ------------------------------- | ------------------------------------------------------------------------------ |
| `main.py`                       | Initializes FastAPI app, routes, `/chat` testing endpoint                      |
| `routes/webhook.py`             | Handles LINE webhook events and binds them to `line_handler`                   |
| `handlers/line_handler.py`      | Parses and processes LINE messages, decides if Gemini API should be used       |
| `handlers/logic_handler.py`     | Core session logic: handles commands like `new`, `modify`, `translate`, `mail` |
| `handlers/session_manager.py`   | In-memory session tracking per user                                            |
| `handlers/mail_handler.py`      | Formats and sends Gemini output via Gmail SMTP                                 |
| `services/gemini_service.py`    | Wraps Gemini API calls for content generation and translation                  |
| `services/prompt_config.py`     | Stores Gemini system prompts for zh generation, translation, and modification  |
| `utils/email_service.py`        | Low-level Gmail SMTP sender and disclaimer attachment                          |
| `utils/command_sets.py`         | Contains valid command keywords sets                                           |
| `utils/google_drive_service.py` | Uploads Gemini session logs as .txt to Google Drive                            |
| `utils/google_sheets.py`        | Sets up gspread client for Google Sheets                                       |
| `utils/log_to_sheets.py`        | Appends logs to Google Sheet and uploads output to Drive if Gemini used        |

---

## 📓 Gemini Prompt Engineering

* `zh_prompt`: for initial health material generation in zh-TW
* `modify_prompt`: revises existing zh-TW material with user instructions
* `translate_prompt_template`: translates content to user-specified language

> All prompts are formatted to be plain text and compliant with health literacy guidelines.

---

## 📧 Email Sending (via Gmail SMTP)

* Uses `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD`
* Adds disclaimer to each message
* Validates email domain via MX lookup

---

## 📓 Google Sheets Logging

* Every LINE or Gemini interaction is logged
* Includes:

  * Timestamp
  * User ID
  * Input
  * Gemini response preview
  * Action type
  * Gemini output (with Drive link if available)

---

## 🌟 Sample Interaction

```txt
User: new
Bot: 🆕 新對話已開始... 請輸入疾病名稱 + 衛教主題

User: CAD with STEMI s/p POBAS care
Bot: ✅ 中文版衛教內容已產生... (顯示內容)

User: translate
Bot: 🌐 請輸入您要翻譯成的語言...

User: Thai
Bot: 🌐 翻譯完成... (顯示原文+譯文)

User: mail
Bot: 📧 請輸入您要寄送至的 email...

User: example@email.com
Bot: ✅ 已成功寄送衛教內容
```

---

## ⚖️ License

MIT License

---

## 📢 Credits

Developed by **Dr. Kuan-Yuan Chen (陳冠元 醫師)**

Contact: [galen147258369@gmail.com](mailto:galen147258369@gmail.com)

For inquiries, suggestions, or collaboration, please feel free to reach out!
