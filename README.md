Here’s a complete and well-documented `README.md` file for your GitHub repository. It explains how to deploy, use, and understand each part of your **FastAPI + Gemini + LINE chatbot**, including how user sessions and the placeholder email logic work.

---

## 📘 README: Health Education Chatbot using Gemini + LINE

### 💡 Overview

This project is a bilingual health education chatbot powered by **Gemini API**, served via **FastAPI**, and integrated with **LINE Messaging API**.

It enables medical staff or clinics to:

* Generate plain-text health education materials in **English + translated language**
* Receive structured responses on topics like hypertension, wound care, and more
* Interact with users via LINE using commands like `"new"` and `"modify"`
* (Future) Send results to patient emails

---

## 🚀 Features

* ✅ Gemini API (2.5 Flash Preview) for multilingual content generation
* ✅ LINE Messaging API integration with FastAPI webhook
* ✅ Per-user session tracking (isolated chatbot flow for each LINE user)
* ✅ Handles `"new"`, `"modify"`, and `"mail"` commands
* 🔒 Email functionality is **stubbed** and not active (for future release)

---

## 🛠️ Setup & Deployment

### 1. Clone Repository

```bash
git clone https://github.com/your-username/health-edu-bot.git
cd health-edu-bot
```

### 2. Create `.env`

```env
GEMINI_API_KEY=your_gemini_api_key
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Locally

```bash
uvicorn main:app --reload --port 8000
```

### 5. Deploy to Render

* Create a new **Web Service** on [https://render.com](https://render.com)
* Use your GitHub repo and set `main.py` as the entrypoint
* Add the environment variables from `.env` in Render's "Environment" settings

---

## 📡 Endpoints

| Method | Path       | Description                         |
| ------ | ---------- | ----------------------------------- |
| POST   | `/chat`    | Manual testing endpoint for chatbot |
| POST   | `/webhook` | LINE webhook target                 |
| GET    | `/`        | Health check + service info         |

---

## 💬 How the Bot Works (Code Logic)

### 🔄 Session Management

* Each LINE user has a unique session using their `user_id`
* Stored in memory via a `sessions = {}` dictionary
* This allows **multiple users** to chat at once without conflict

### 🤖 `handle_user_message(text, session)`

Central handler that interprets user input. Logic order:

1. **"new"**

   * Resets all session fields
   * Prompts user to enter language

2. **awaiting\_email**

   * If set, only accepts valid email
   * Returns a placeholder "email feature in development" message

3. **"mail"**

   * If a Gemini response exists, prompt user for their email

4. **"modify"**

   * Sends the `last_response` + new instruction back to Gemini

5. **language → disease → topic**

   * Step-by-step prompt collection
   * Triggers Gemini generation when all fields are filled

6. **Default: modification**

   * If no keywords match, any message after generation is treated as a revision

---

### 🧠 Gemini Prompt Strategy

* System prompt instructs Gemini to:

  * Output in plain text (no Markdown)
  * Use simple structure:

    ```
    # Section
     - Point
     - Point
    ```
  * First in English, then in the chosen language
  * Avoid external references or URLs

---

### 📧 Email Logic

* If user types `"mail"`, they're prompted for a valid email address
* Regex validates the email
* Feature is **disabled** — reply confirms email was received but sending is not implemented

---

## ✏️ Example Usage Flow (LINE)

```
User: new
Bot: 🆕 已開始新的對話。請輸入您希望翻譯的語言（例如：泰文、越南文）...
User: Thai
Bot: 🌐 已設定語言。請輸入疾病名稱：
User: Hypertension
Bot: 🩺 已設定疾病。請輸入您想要的衛教主題：
User: Blood pressure monitoring
Bot: (Gemini returns bilingual explanation)
Bot: 📌 若您想將衛教資料寄送 email，請輸入 "Mail"...
```

---

## 📎 Requirements

```txt
fastapi
uvicorn[standard]
pydantic
python-dotenv
google-generativeai
line-bot-sdk
```

Install with:

```bash
pip install -r requirements.txt
```

---

## 📌 Future Plans

* [ ] Add Gmail API to send real email to users
* [ ] Host session data in Redis or database
* [ ] Use Quick Reply or Flex Messages on LINE
* [ ] Export response as PDF for printing or sharing

---

## 📮 Questions or Contributions

Feel free to open an issue or submit a pull request.

---
