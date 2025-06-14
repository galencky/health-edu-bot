# MedEdBot - Medical Education LINE Chatbot

A LINE chatbot that provides medical education content and real-time medical chat assistance powered by Google Gemini AI.

## 🏗️ Architecture Overview

### Core Components

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   LINE Users    │────▶│  LINE API    │────▶│   FastAPI App   │
└─────────────────┘     └──────────────┘     └────────┬────────┘
                                                       │
                    ┌──────────────────────────────────┼──────────────────────────────────┐
                    │                                  │                                  │
              ┌─────▼─────┐                    ┌──────▼──────┐                   ┌───────▼───────┐
              │  Webhook   │                    │   Handlers  │                   │   Services    │
              │  Router    │                    │             │                   │               │
              └─────┬─────┘                    └──────┬──────┘                   └───────┬───────┘
                    │                                  │                                    │
         ┌──────────┴──────────┐          ┌───────────┴───────────┐            ┌──────────┴──────────┐
         │ Message Validation  │          │ • line_handler        │            │ • gemini_service    │
         │ Signature Verify    │          │ • logic_handler       │            │ • tts_service       │
         └─────────────────────┘          │ • medchat_handler     │            │ • stt_service       │
                                          │ • mail_handler        │            │ • prompt_config     │
                                          │ • session_manager_v2  │            └─────────────────────┘
                                          └───────────┬───────────┘
                                                      │
                                          ┌───────────▼───────────┐
                                          │    Utilities          │
                                          │ • database            │
                                          │ • validators          │
                                          │ • rate_limiter        │
                                          │ • memory_storage      │
                                          │ • google_drive        │
                                          └───────────────────────┘
```

### How Components Work Together

1. **Webhook Entry Point** (`routes/webhook.py`)
   - Receives LINE webhook events
   - Validates LINE signature for security
   - Routes messages to appropriate handlers

2. **Message Handlers** (`handlers/`)
   - `line_handler.py`: Processes text and audio messages from LINE
   - `logic_handler.py`: Implements command logic and routing
   - `medchat_handler.py`: Manages medical chat conversations
   - `session_manager_v2.py`: Thread-safe session management

3. **AI Services** (`services/`)
   - `gemini_service.py`: Google Gemini AI integration for content generation
   - `tts_service.py`: Text-to-speech conversion using Gemini
   - `stt_service.py`: Speech-to-text for voice messages
   - `prompt_config.py`: System prompts for different modes

4. **Data & Storage** (`utils/`)
   - `database.py`: PostgreSQL operations for logging and analytics
   - `memory_storage.py`: In-memory storage for cloud deployments
   - `google_drive_service.py`: Backup audio files to Google Drive

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database
- LINE Messaging API account
- Google Cloud account with Gemini API access
- (Optional) Google Drive API for file backup

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/mededbot.git
   cd mededbot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your credentials:
   ```env
   # LINE Configuration
   LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
   LINE_CHANNEL_SECRET=your_line_channel_secret
   
   # Google Gemini API
   GEMINI_API_KEY=your_gemini_api_key
   
   # Database (PostgreSQL)
   DATABASE_URL=postgresql://user:password@localhost:5432/mededbot
   
   # Email Configuration (for sending education materials)
   GMAIL_ADDRESS=your_gmail@gmail.com
   GMAIL_APP_PASSWORD=your_app_specific_password
   
   # Google Drive (optional)
   GOOGLE_DRIVE_FOLDER_ID=your_folder_id
   GOOGLE_CREDS_B64=base64_encoded_service_account_json
   
   # Application Settings
   PORT=10001
   BASE_URL=https://your-domain.com  # Or ngrok URL for local testing
   ```

5. **Initialize database**
   ```bash
   python init_db.py
   ```

6. **Run the application**
   ```bash
   python main.py
   ```

### Docker Setup

1. **Using Docker Compose**
   ```bash
   docker-compose up -d
   ```

2. **For Synology NAS**
   ```bash
   docker-compose -f docker-compose.synology.yml up -d
   ```

## 📱 LINE Bot Configuration

1. **Create LINE Channel**
   - Go to [LINE Developers Console](https://developers.line.biz/)
   - Create a new Messaging API channel
   - Note your Channel Access Token and Channel Secret

2. **Configure Webhook**
   - Set webhook URL to: `https://your-domain.com/webhook`
   - Enable webhook
   - Disable auto-reply messages

3. **For Local Development**
   - Use [ngrok](https://ngrok.com/) to expose local server:
     ```bash
     ngrok http 10001
     ```
   - Update LINE webhook URL with ngrok URL

## 🛠️ Features & Commands

### User Commands

- **`new`** - Start new conversation or return to main menu
- **`秘書`** - Enter medical chat mode
- **`mail`/`寄送`** - Email current education content
- **`speak`** - Generate audio for last response
- **`中文`/`English`/`日本語`** - Switch chat language

### Modes

1. **Education Mode** (default)
   - Browse and read medical education materials
   - Interactive menu navigation
   - Multi-language support

2. **Medical Chat Mode**
   - Real-time medical Q&A
   - Voice message support
   - Context-aware responses

### Voice Features

- **Voice Messages**: Automatically transcribed and can be translated
- **Text-to-Speech**: Generate audio for any response
- **Multi-language**: Supports various languages for both STT and TTS

## 🔒 Security Features

- **Input Validation**: Prevents SQL injection and path traversal
- **Rate Limiting**: Protects against API abuse
- **Session Management**: Thread-safe user session handling
- **Signature Verification**: Validates all LINE webhook requests

## 📊 Database Schema

```sql
-- Chat logs
CREATE TABLE chat_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    user_message TEXT,
    bot_reply TEXT,
    action_type VARCHAR(100),
    gemini_call BOOLEAN,
    gemini_output_url TEXT
);

-- TTS logs
CREATE TABLE tts_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    text TEXT,
    audio_filename VARCHAR(255),
    audio_url TEXT,
    drive_link TEXT,
    status VARCHAR(50)
);

-- Voicemail logs  
CREATE TABLE voicemail_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    audio_filename VARCHAR(255),
    transcription TEXT,
    translation TEXT,
    drive_link TEXT
);
```

## 🚀 Deployment

### Deploy to Render.com

1. **Fork this repository**

2. **Create new Web Service on Render**
   - Connect your GitHub repository
   - Use `render.yaml` for configuration
   - Set environment variables in Render dashboard

3. **Configure Build**
   ```bash
   # Automatic with render.yaml
   pip install -r requirements.txt
   ```

4. **Start Command**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

### Deploy to Other Platforms

The app is designed to work on any platform that supports:
- Python 3.11+
- PostgreSQL
- Persistent or ephemeral file storage
- Environment variables

For ephemeral filesystems (like Heroku), the app automatically uses in-memory storage for temporary files.

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE bot access token | Yes |
| `LINE_CHANNEL_SECRET` | LINE channel secret | Yes |
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `GMAIL_ADDRESS` | Gmail for sending emails | Yes |
| `GMAIL_APP_PASSWORD` | Gmail app password | Yes |
| `BASE_URL` | Your app's public URL | Yes |
| `PORT` | Server port (default: 10001) | No |
| `GOOGLE_DRIVE_FOLDER_ID` | Drive folder for backups | No |
| `GOOGLE_CREDS_B64` | Base64 encoded service account | No |
| `LOG_LEVEL` | Logging level (default: INFO) | No |
| `USE_MEMORY_STORAGE` | Force memory storage | No |

### Storage Configuration

The app automatically detects the deployment environment:
- **Local/Persistent FS**: Uses disk storage for audio files
- **Cloud/Ephemeral FS**: Uses in-memory storage with LRU eviction

## 📝 Logging

The app uses structured logging with different levels:
- **Database operations**: Concise success/failure messages
- **API calls**: Rate limiting and retry information  
- **File operations**: Upload/deletion status
- **Errors**: Full stack traces for debugging

Logs are output to stdout and can be collected by your deployment platform.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google Gemini API for AI capabilities
- LINE Messaging API for chat platform
- FastAPI for the web framework
- PostgreSQL for reliable data storage