# Mededbot - 多語言衛教 AI Chatbot

A multilingual health education chatbot built with **FastAPI**, integrated with **LINE Messaging API** and **Google Gemini API**, supporting dynamic patient education content generation, translation, email delivery, and logging to Google Sheets and Drive.

一個以 **FastAPI** 建構的多語言健康衛教聊天機器人，整合 **LINE Messaging API** 與 **Google Gemini API**，支援動態生成衛教內容、自動翻譯、寄送電子郵件，以及紀錄資料至 Google Sheets 和 Google Drive。

---

## 🚀 Features 功能特色

* ✅ LINE-compatible multilingual chatbot interface  
      支援 LINE 的多語言聊天介面  

* ✅ Gemini API integration for generating 保健 content in Traditional Chinese (zh-TW)  
      整合 Gemini API，自動生成繁體中文健康衛教內容  

* ✅ One-click modification, translation, and emailing of content  
      一鍵修改、翻譯與寄送衛教資料  

* ✅ Email validation with MX record checking  
      電子郵件格式與 MX 記錄驗證功能  

* ✅ Logging interaction data to Google Sheets and Gemini output to Google Drive  
      將對話與 Gemini 回應記錄至 Google Sheets 與 Google Drive  
      
* ✅ Modular, scalable architecture  
      模組化架構，便於擴充與維護

---

## 🌐 Demo Endpoints 示範端點

| Endpoint   | Description (EN)                     | 描述（中文）                       |
| ---------- | ------------------------------------ | ---------------------------------- |
| `/`        | Health check + basic endpoint info  | 健康檢查與基本端點資訊               |
| `/chat`    | Chatbot testing without LINE frontend | 測試聊天功能（不經由 LINE 前端）     |
| `/ping`    | Health check for uptime monitoring  | 運作狀態監控                        |
| `/webhook` | LINE webhook receiver               | 接收 LINE webhook 事件             |

---

## 🚪 Setup & Installation 安裝步驟

### 1. Clone and prepare environment 下載並準備執行環境

```
git clone https://github.com/YOUR_NAME/mededbot.git
cd mededbot
python -m venv venv
source venv/bin/activate  # Windows 請改用 venv\Scripts\activate
pip install -r requirements.txt
```

### 2. env Configuration 設定 .env 檔案

Create a `.env` file with:
請建立一個 `.env` 檔案並填入以下內容：

```env
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_CHANNEL_SECRET=...
GEMINI_API_KEY=...
GMAIL_ADDRESS=...
GMAIL_APP_PASSWORD=...
GOOGLE_CREDS_B64=...  # base64 格式的 Google credentials.json
GOOGLE_DRIVE_FOLDER_ID=...  # 存放 Gemini 記錄的 Google Drive 資料夾 ID
```

---

## 🤖 How It Works 使用流程

### ⚡ User Flow (via LINE) 使用者流程（透過 LINE）

1. **Start**: User enters `new` to initiate a session
   **開始**：輸入 `new` 開始新對話
2. **Input Topic**: User enters health topic
   **輸入主題**：使用者輸入衛教主題
3. **Gemini** generates Traditional Chinese material
   **Gemini 生成**：產生繁體中文內容
4. **Modify**: Optional user adjustments via `modify`
   **修改內容**：可選擇輸入 `modify` 進行微調
5. **Translate**: Optional translation via `translate`
   **翻譯**：輸入 `translate` 進行語言翻譯
6. **Mail**: Sends content via `mail`
   **寄送**：輸入 `mail` 將內容寄出

### 📁 Core Modules and Their Responsibilities 核心模組與職責

| File / Module                   | Description (EN)                             | 中文說明                                      |
| ------------------------------- | -------------------------------------------- | ----------------------------------------- |
| `main.py`                       | Starts app, routes `/chat`                   | 啟動主應用與測試端點設定                              |
| `routes/webhook.py`             | Handles incoming LINE webhook events         | 接收與處理 LINE webhook 事件                     |
| `handlers/line_handler.py`      | Parses messages, triggers Gemini if needed   | 處理 LINE 訊息並判斷是否觸發 Gemini                  |
| `handlers/logic_handler.py`     | Manages main user session logic              | 處理 `new`、`modify`、`translate`、`mail` 指令邏輯 |
| `handlers/session_manager.py`   | Tracks per-user sessions                     | 使用者會話追蹤（記憶上下文）                            |
| `handlers/mail_handler.py`      | Sends email via Gmail SMTP                   | 使用 Gmail SMTP 寄送郵件                        |
| `services/gemini_service.py`    | Calls Gemini API for content and translation | 呼叫 Gemini API 生成或翻譯內容                     |
| `services/prompt_config.py`     | Stores prompt templates                      | 儲存 Gemini 指令提示模版                          |
| `utils/email_service.py`        | Low-level SMTP operations with disclaimer    | 處理 SMTP 寄信與加註免責聲明                         |
| `utils/command_sets.py`         | Valid command keywords                       | 合法指令關鍵字集                                  |
| `utils/google_drive_service.py` | Uploads logs as `.txt` to Drive              | 將內容上傳為 .txt 至 Google Drive                |
| `utils/google_sheets.py`        | gspread client setup                         | 建立 Google Sheets 連線                       |
| `utils/log_to_sheets.py`        | Logs chat and uploads to Drive               | 記錄對話並上傳 Gemini 內容至雲端                      |

---

### 📓 Gemini Prompt Engineering 提示詞設計

* `zh_prompt`: Generates health material in Traditional Chinese
  產生繁體中文衛教內容
* `modify_prompt`: Applies user modifications to zh content
  根據使用者需求修改原始內容
* `translate_prompt_template`: Translates into user-selected language
  翻譯為指定語言

> All prompts follow health literacy and plain language guidelines.
> 所有提示詞設計皆符合健康素養與淺顯易懂原則。


---

### 🧠 Original System Instructions for Gemini Models  完整原始提示詞

<details>
<summary>📘 zh_prompt — 中文衛教生成</summary>

```text
You are an AI health education expert helping create plain-text patient education materials for the general public in Traditional Chinese. Follow these instructions strictly:

1. All output must be in Traditional Chinese (`zh-tw`) and in plain text. Do not use Markdown, HTML, or any special formatting symbols like `*`, `_`, `#` (for markdown), or backticks.
2. Acceptable formatting structure:
   - Use a clear title at the top (e.g., `主題：高血壓的日常控制`)
   - Use simple bullet points with dashes (`-`) for subsections, e.g.:
     - 標題
     - 概要
     - 詳細說明（4–6 條說明）
     - 常見問答（2–3 組問答）
     - 建議行動（1–2 項具體建議）
     - 聯絡資訊
3. Do not add emojis to every line. Emojis may be used sparingly in section headers or to highlight key reminders (e.g., ⭐ ⚠️ ✅ ❓ 📞), but not excessively.
4. Language should be clear, supportive, and suitable for a middle-school reading level. Use full sentences that explain what something is, why it matters, and how to act on it.
5. Sentence length can be moderate to ensure clarity. Avoid overly simplistic or fragmented instructions.
6. Avoid scolding, alarming, or fear-based tones. Be supportive and encouraging.
7. Do not include links or citations, even if referring to trusted sources. The content must be self-contained.

Based on the provided topic, generate a complete and structured patient education message in Traditional Chinese, following the rules above exactly.
```

</details>

<details>
<summary>🛠️ modify_prompt — 中文微調</summary>

```text
You are a health education assistant helping revise existing plain-text health content in Traditional Chinese (`zh-tw`). The original content was generated for the public based on current clinical knowledge.

Please revise the text below according to the user’s instructions, but keep the original structure, formatting, and tone. Do not remove necessary sections.

Constraints:
- Do not use Markdown or HTML.
- Use only dash (`-`) bullets and clear section headers.
- Preserve formatting and use plain Traditional Chinese.

Your task:
Given the original text and user modification instructions, revise the text as requested and return the full corrected result in `zh-tw`.
```

</details>

<details>
<summary>🌐 translate_prompt_template — 翻譯提示詞</summary>

```text
You are a medical translation assistant. Please translate the following medical education content into {lang}. Use plain text only, and make the translation clear and easy to understand. Do not add any extra explanations or comments.
```

</details>


---

### 📧 Email Sending (via Gmail SMTP) 郵件寄送

* Uses `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD`
  使用 Gmail 地址與應用程式密碼登入
* Adds disclaimer to all messages
  所有信件均附加免責聲明
* Validates email domains using MX lookup
  驗證收件人信箱網域是否有效

---

### 📓 Google Sheets Logging 使用紀錄

* Logs every Gemini or LINE interaction
  所有使用紀錄皆會儲存
* Details include:
  包含以下資訊：

  * Timestamp 時間戳記
  * User ID 使用者 ID
  * Input 輸入內容
  * Gemini preview Gemini 回應摘要
  * Action type 操作類型
  * Gemini output (Drive link if available) Gemini 產出（含雲端連結）

---

### 🌟 Sample Interaction 範例對話

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

### ✂️ LINE Message Truncation Logic 訊息長度處理邏輯

Due to LINE’s message limits (max **5 messages per reply**, each **\~4000 chars**), this bot uses smart truncation with guidance:
由於 LINE 有訊息限制（最多 **5 則訊息**，每則約 **4000 字元**），本機器人實作了智慧截斷機制與提醒提示：

* `zh_output` limited to 2 messages
  中文內容最多顯示 2 則
* `translated_output` limited to 1 message
  翻譯內容最多顯示 1 則
* 4th message gives follow-up options
  第四則為操作選項提示
* If too long, 5th message says:
  如超出限制，第五則提示如下：

```
⚠️ Due to LINE message length limits, some content is not shown.
Type "mail" or "寄送" to receive the full material by email.

⚠️ 因 LINE 訊息長度限制，部分內容未顯示。
請輸入 "mail" 或 "寄送" 以透過電子郵件取得完整內容。
```

---

## ⚖️ License 授權條款

MIT License
MIT 授權條款

---

## 📢 Credits 開發者資訊

Developed by **Kuan-Yuan Chen, M.D.**
開發者：**陳冠元 醫師**

Contact 聯絡方式：[galen147258369@gmail.com](mailto:galen147258369@gmail.com)

歡迎提供建議、合作邀約或回饋意見！
For suggestions, collaboration, or feedback — feel free to reach out!