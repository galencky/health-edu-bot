# Mededbot – 多語言衛教 AI 聊天機器人

> 以 **FastAPI + LINE Messaging API + Google Gemini API** 打造的衛教內容生成與即時醫療翻譯服務，部署於 **Render** 免費 Web Service，並透過 **UptimeRobot** 每 5 分鐘喚醒，確保 24 × 7 線上服務。

---

## 內容快速導覽

1. [專案簡介](#專案簡介)
2. [功能特色](#功能特色)
3. [系統架構](#系統架構)
4. [快速開始](#快速開始)
5. [Render 部署指南](#render-部署指南)
6. [LINE Webhook 設定](#line-webhook-設定)
7. [環境變數說明](#環境變數說明)
8. [指令與操作流程](#指令與操作流程)
9. [常見問題 FAQ](#常見問題-faq)
10. [授權與聯絡方式](#授權與聯絡方式)

---

## 專案簡介

Mededbot 旨在協助醫療人員以繁體中文撰寫結構化衛教單張，並可一鍵翻譯、修改與寄送 Email。另提供 **MedChat** 模式，支援中文→任意語言之即時醫療對話翻譯，加速與外國患者溝通。

此專案使用：

* **FastAPI**：非同步 Python Web Framework。
* **LINE Messaging API**：聊天介面與 Webhook。
* **Google Gemini API**：生成與翻譯大型語言模型（LLM）。
* **Google Drive / Sheets**：日誌與檔案備份。
* **Render Free Web Service**：零成本雲端部署。
* **UptimeRobot**：定時 `/ping` 監測，避免 Render 服務休眠。

---

## 功能特色

| 模組                    | 功能概要                                                                 |
| --------------------- | -------------------------------------------------------------------- |
| **Education 模式**      | 依「疾病名稱 + 衛教主題」產生條列式衛教單張 → 可 `modify` 調整 → `translate` 翻譯 → `mail` 寄送 |
| **MedChat 模式**        | 將口語中文平易化後翻譯至指定語言，並附 "Do you understand?" 確認句                         |
| **Google Sheets Log** | 將用戶輸入、Gemini 結果、動作類型寫入試算表                                            |
| **Google Drive 備份**   | 生成之全文 .txt 以 HYPERLINK 形式儲存雲端                                        |
| **Email 寄送**          | 透過 Gmail SMTP，附免責聲明郵寄衛教內容                                            |
| **Session 管理**        | 以 in‑memory dict 追蹤對話狀態、模式、產出                                        |

---

## 系統架構

### 流程概述

```
LINE User → LINE Webhook → FastAPI /webhook → handlers.line_handler
              │                                 │
              │                                 └─> handlers.logic_handler ↔ Gemini API
              │                                                     │
              │                                   Google Drive / Google Sheets
              └── /ping (UptimeRobot)
```

### 專案目錄結構

```
.
├── main.py                # 入口點 + /ping /chat 測試端點
├── routes/
│   └── webhook.py         # 綁定 LINE WebhookHandler
├── handlers/
│   ├── line_handler.py    # LINE 訊息分段、回覆
│   ├── logic_handler.py   # 核心指令解析
│   ├── medchat_handler.py # 即時翻譯流程
│   ├── mail_handler.py    # Gmail 寄送
│   └── session_manager.py # 使用者 Session
├── services/
│   ├── gemini_service.py  # Gemini 呼叫封裝
│   └── prompt_config.py   # 系統 / 修改 / 翻譯 Prompt
└── utils/
    ├── command_sets.py    # 指令字集合
    ├── email_service.py   # SMTP 寄信
    ├── google_drive_service.py
    ├── google_sheets.py
    └── log_to_sheets.py   # 寫入試算表 + 上傳 Drive
```

---

## 快速開始

### 系統需求

* Python ≥ 3.11
* pip / venv / poetry (擇一)

### 1. 下載與安裝

```bash
# 取得程式碼
$ git clone https://github.com/<your‑repo>/mededbot.git
$ cd mededbot

# 安裝依賴
$ pip install -r requirements.txt
```

### 2. 設定環境變數

> 詳細定義請見下節「[環境變數說明](#環境變數說明)」。在本機可於根目錄建立 **.env** 檔：

```dotenv
LINE_CHANNEL_ACCESS_TOKEN=...  # LINE Bot Token
LINE_CHANNEL_SECRET=...
GEMINI_API_KEY=...
GMAIL_ADDRESS=your@gmail.com
GMAIL_APP_PASSWORD=your_app_pass
GOOGLE_CREDS_B64=<base64_JSON>
GOOGLE_DRIVE_FOLDER_ID=...
```

### 3. 啟動開發伺服器

```bash
$ python main.py
# 或
$ uvicorn main:app --reload --host 0.0.0.0 --port 10000
```

### 4. 測試

* 瀏覽 `http://localhost:10000/`       → 健康檢查
* `POST /chat` with JSON `{"message":"new"}` → 測試端點

---

## Render 部署指南

### 1. 建立 Web Service

1. 登入 [Render](https://render.com/) → **New +** → **Web Service**。
2. 連結 GitHub 倉庫，分支選擇 **main**。

### 2. Build 與 Start 指令

| 欄位            | 指令                                             |
| ------------- | ---------------------------------------------- |
| Build Command | `pip install -r requirements.txt`              |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

### 3. 環境變數

於 Render 介面 **Environment → Add Environment Variable**，填入與本機相同之變數。

### 4. 免費方案睡眠 & UptimeRobot

* Render 免費方案若 15 分鐘無流量即休眠，首次喚醒需 \~30 秒。
* 於 [UptimeRobot](https://uptimerobot.com/) 新增 **HTTP(s) Monitor**：

  * **URL**：`https://<your‑render‑service>.onrender.com/ping`
  * **Interval**：5 分鐘。
* UptimeRobot 會定期 GET `/ping`，保持服務常駐。

> **注意**：Render 官方允許低頻率健康檢查；設定過高 (≤1 min) 可能違反 TOS。

---

## LINE Webhook 設定

1. 於 LINE Developers Console 建立 **Messaging API Channel**。
2. 將 **Webhook URL** 設為：

```
https://<your‑render‑service>.onrender.com/webhook
```

3. 啟用 Webhook、發佈 Bot。
4. 把 `LINE_CHANNEL_ACCESS_TOKEN`、`LINE_CHANNEL_SECRET` 放入 Render 變數。

---

## 環境變數說明

| 變數                          | 說明                                    | 必要 |
| --------------------------- | ------------------------------------- | -- |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot Long‑Lived Token             | ✅  |
| `LINE_CHANNEL_SECRET`       | LINE Channel Secret                   | ✅  |
| `GEMINI_API_KEY`            | Google Gemini API Key                 | ✅  |
| `GMAIL_ADDRESS`             | Gmail 寄信帳號                            | ✅  |
| `GMAIL_APP_PASSWORD`        | Gmail 應用程式密碼                          | ✅  |
| `GOOGLE_CREDS_B64`          | 以 Base64 編碼之 GCP Service Account JSON | ✅  |
| `GOOGLE_DRIVE_FOLDER_ID`    | Drive 資料夾 ID，用於上傳 .txt                | ✅  |

---

## 指令與操作流程

| 階段            | 指令/訊息              | 機器人回應                  |
| ------------- | ------------------ | ---------------------- |
| **開始**        | `new` / `開始`       | 初始化，要求選擇 `ed` 或 `chat` |
| **選擇模式**      | `ed` / `衛教`        | 進入 Education 模式        |
|               | `chat` / `聊天`      | 進入 MedChat 模式          |
| **Education** | 輸入 `疾病 + 主題`       | 產生中文版衛教單張              |
|               | `modify` / `修改`    | 進入修改 → 提供修改指示          |
|               | `translate` / `翻譯` | 指定語言 → 產生譯文            |
|               | `mail` / `寄送`      | 輸入 Email → Gmail 寄送    |
| **MedChat**   | 未設定語言時輸入目標語言       | 例如 `英文` → 設定成功         |
|               | 任意中文訊息             | 回傳平易化中文 + 目標語言翻譯       |

---

## 常見問題 FAQ

**Q1 › API 呼叫延遲多久？**

* 衛教模式（ed）平均約 **15 秒**。
* 聊天模式（chat）平均約 **25 秒**。（Gemini 需雙向處理：簡化＋翻譯）

**Q2 › 機器人使用了哪些提示詞（prompts）？**

* `zh_prompt`：生成繁體中文衛教內容。
* `translate_prompt_template`：進行跨語言翻譯並保留版面。
* `modify_prompt`：依使用者指示微調衛教文字。
* `plainify_prompt`：將口語或混雜醫學縮寫整理成平易近人的中文。
* `confirm_translate_prompt`：產出目標語言翻譯並回覆「是否理解？」短句。

> 以上提示詞均位於 `services/prompt_config.py`，可自行客製化。

**Q3 › UptimeRobot Ping 是否違規？** — Render 官方文件允許「適度」健康檢查，5 分鐘以上屬安全區間。

**Q4 › 如何替換 SMTP？** — 修改 `utils/email_service.py`，支援 SendGrid / SES 等。

---

## 授權與聯絡方式

* **License**：MIT
* **Maintainer**：陳冠元 ([galen147258369@gmail.com](mailto:galen147258369@gmail.com))

歡迎提供建議、合作邀約或回饋意見！
For suggestions, collaboration, or feedback — feel free to reach out!