# MedEdBot – 衛教翻譯聊天機器人

**作者：** 陳冠元 醫師 (Kuan-Yuan Chen, M.D.)  
**聯絡信箱：** galen147258369@gmail.com  

---

## 🚀 專案概述

MedEdBot 是一款多語言健康教育與即時翻譯聊天機器人，採用 FastAPI、LINE Messaging API 與 Google Gemini AI 模型打造。主要功能包括：

- **衛教單張生成**  
  產出結構化的繁體中文「衛教單張」，可進行內容修改、翻譯至多種語言，並透過 LINE 或 Email 傳送。  
- **即時聊天翻譯（MedChat）**  
  中–外語雙向即時翻譯，並可選擇產出 AI 朗讀音訊。  
- **語音留言轉文字與翻譯**  
  上傳 LINE 語音訊息後，使用 Gemini STT 轉錄，再依用戶需求翻譯。  
- **文字轉語音（TTS）**  
  AI 生成 WAV 檔案，可在聊天室中播放，並同步上傳至 Google Drive & Sheets 作為記錄。  
- **互動日誌與分析**  
  所有對話與音訊處理過程均備份至 Google Drive，並在 Google Sheets 中記錄分析。

---

## 📂 專案結構

~~~

.
├── main.py                   # FastAPI 應用進入點
├── routes/
│   └── webhook.py            # LINE Webhook 路由與註冊
├── handlers/
│   ├── line\_handler.py       # 處理 LINE 文字與音訊事件
│   ├── logic\_handler.py      # 模式與命令的核心調度器
│   ├── session\_manager.py    # 使用者 Session 管理（記憶狀態）
│   ├── medchat\_handler.py    # 即時翻譯聊天邏輯
│   └── mail\_handler.py       # 衛教單張 Email 寄送邏輯
├── services/
│   ├── gemini\_service.py     # Google Gemini API 包裝
│   ├── prompt\_config.py      # 系統提示語與模板
│   ├── stt\_service.py        # Gemini 語音轉文字服務
│   └── tts\_service.py        # Gemini 文字轉語音服務
├── utils/
│   ├── command\_sets.py       # 命令關鍵詞集
│   ├── email\_service.py      # SMTP 寄信輔助
│   ├── google\_drive\_service.py  # Google Drive 上傳輔助
│   ├── google\_sheets.py      # Google Sheets 操作輔助
│   ├── log\_to\_sheets.py      # 互動紀錄寫入 Sheets
│   ├── tts\_log.py            # TTS 音訊上傳與記錄
│   └── voicemail\_drive.py    # 語音留言上傳 Drive
├── tts\_audio/                # 本地儲存生成的 WAV 檔案
├── voicemail/                # 下載的 LINE 語音檔案
├── .env                      # 環境變數設定（不納入版本庫）
└── requirements.txt          # Python 相依套件清單

~~~

---

## 🔧 前置需求

- Python 3.9 以上  
- LINE Messaging API Channel（Access Token、Channel Secret）  
- Google Cloud Service Account JSON（以 Base64 編碼，設定於 `GOOGLE_CREDS_B64`）  
- Gmail 帳號與應用程式專用密碼  
- 用於日誌與音訊的 Google Drive 資料夾 ID  
- 可公開存取的服務網址 (`BASE_URL`)，用於靜態音訊串流

---

## ⚙️ 環境設定

在專案根目錄建立 `.env`，填入以下內容：

~~~
-LINE
LINE_CHANNEL_ACCESS_TOKEN=你的_line_channel_access_token
LINE_CHANNEL_SECRET=你的_line_channel_secret

-Gemini API
GEMINI_API_KEY=你的_google_gemini_api_key

-SMTP Email (Gmail)
GMAIL_ADDRESS=你的_gmail_信箱
GMAIL_APP_PASSWORD=應用程式專用密碼

-Google Drive & Sheets
GOOGLE_DRIVE_FOLDER_ID=你的_drive_folder_id
GOOGLE_CREDS_B64=base64_編碼後的_service_account_json

-服務 URL (用於 TTS 音訊串流)
BASE_URL=https://your.domain.com

~~~
---

## 📥 安裝步驟

1. 取得程式碼：

   ```bash
   git clone https://github.com/your-org/mededbot.git
   cd mededbot
   ```
2. 安裝相依套件：

   ```bash
   pip install -r requirements.txt
   ```
3. 設定並確認 `.env` 已正確填寫。

---

## 🏃 本地執行

```bash
uvicorn main:app --host 0.0.0.0 --port 10000 --reload
```

* **靜態音訊**：`http://localhost:10000/static/<filename>.wav`
* **LINE Webhook**：`POST /webhook`
* **測試聊天**：`POST /chat`

  ```json
  { "message": "你好" }
  ```

---

## 📍 API 介面

| 路徑         | 方法       | 說明                           |
| ---------- | -------- | ---------------------------- |
| `/`        | GET      | 健康檢查 & 顯示可用端點                |
| `/ping`    | GET/HEAD | 回傳 JSON `{ "status": "ok" }` |
| `/chat`    | POST     | 測試專用 API（非 LINE）             |
| `/webhook` | POST     | LINE Webhook 接收文字與音訊事件       |

---

## 💬 使用說明

1. **開始新流程**
   發送 `new` 或 `開始`
2. **選擇模式**

   * `ed`／`education`／`衛教` → 衛教單張模式
   * `chat`／`聊天` → 即時翻譯聊天模式
3. **衛教單張模式**

   * 輸入 `<疾病名稱> <衛教主題>` → 生成繁中衛教單張
   * `modify`／`修改` → 修改已生成內容
   * `translate`／`翻譯` → 翻譯至目標語言
   * `mail`／`寄送` → Email 單張
   * `speak`／`朗讀` → （需先翻譯後）產生 TTS
4. **即時聊天模式**

   * 首次輸入目標語言（如 `英文`）
   * 接著輸入任意文字 → 回傳平實化＋翻譯結果
   * `speak`／`朗讀` → 產生最後翻譯文字的 TTS
5. **語音留言**

   * 上傳 LINE 語音訊息 → 機器人回傳文字轉錄
   * 回覆 `<lang>` 或 `new`／`無` → 執行翻譯或取消

---

## 🔍 日誌與稽核

* **文字紀錄**：以 `.txt` 檔上傳至 Google Drive，並記錄於 Google Sheets（`ChatbotLogs`）。
* **TTS 音訊**：保存在 `tts_audio/`，並同步上傳至 Drive，記錄於 `TTSLogs`。
* **語音留言**：存放於 `voicemail/`，並備份至 Drive。

---

## 🛠️ 擴充與客製化

* **提示語修改**：編輯 `services/prompt_config.py`，調整系統提示與模板。
* **命令集擴充**：更新 `utils/command_sets.py`，新增或修改指令關鍵詞。
* **Session 儲存**：將 `handlers/session_manager.py` 中的記憶體儲存改為 Redis 或資料庫，以達持久化。
* **部屬**：可使用 Docker 容器化，透過 HTTPS 暴露 `/static` 與 `/webhook`，並於 LINE 後台設定 webhook URL。

---

## 📜 授權條款

本專案採用 MIT License 釋出。

---

感謝使用 MedEdBot！
— 陳冠元醫師 (Kuan-Yuan Chen, M.D.)
[galen147258369@gmail.com](mailto:galen147258369@gmail.com)

