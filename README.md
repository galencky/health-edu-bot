# MedEdBot - Multilingual Medical Education AI Assistant 🏥🤖

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![LINE](https://img.shields.io/badge/LINE-Messaging_API-00B900.svg)](https://developers.line.biz/en/)
[![Gemini](https://img.shields.io/badge/Google-Gemini_2.5-4285F4.svg)](https://ai.google.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-316192.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-ready multilingual medical education chatbot that provides patient education materials in 100+ languages via LINE messaging platform. Powered by Google Gemini 2.5 AI for advanced content generation, real-time translation, and voice interaction capabilities.

## 🌟 Key Features

### Core Capabilities
- **🌍 100+ Language Support**: From major languages (English, Spanish, Chinese) to regional dialects (Taiwanese, Hakka, indigenous languages)
- **🎙️ Voice Interaction**: Advanced speech-to-text transcription and text-to-speech with natural voice synthesis
- **📋 Patient Education Materials**: AI-generated, medically accurate education sheets tailored to patient needs
- **💬 Dual Mode Operation**: 
  - **Education Mode**: Generate structured patient education materials
  - **Chat Mode**: Natural medical Q&A conversations
- **📧 Multi-channel Delivery**: Share materials via LINE messages, email, or audio files
- **🔍 Evidence-based Content**: Automatic citation of credible medical sources with Google Search integration
- **📊 Comprehensive Analytics**: Full interaction logging to PostgreSQL with Google Drive backup

### Technical Features
- **⚡ High Performance**: Async architecture with FastAPI for concurrent user handling
- **🔒 Enterprise Security**: HTTPS, signature verification, and secure credential management
- **🐳 Container Ready**: Dockerized for easy deployment and scaling
- **🔄 Session Persistence**: Maintain conversation context across interactions
- **♻️ Automatic Cleanup**: Memory management and file cleanup systems
- **📈 Scalable Architecture**: Database connection pooling and optimized resource usage

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [System Requirements](#-system-requirements)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [Deployment](#-deployment)
- [API Reference](#-api-reference)
- [Database Schema](#-database-schema)
- [Security](#-security)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Quick Start

### Prerequisites Check
```bash
# Check Python version (requires 3.11+)
python --version

# Check PostgreSQL (or use Neon.tech cloud database)
psql --version
```

### 1-Minute Setup
```bash
# Clone and enter directory
git clone https://github.com/yourusername/mededbot.git
cd mededbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp .env.example .env
nano .env  # Add your API keys and credentials

# Initialize database
python init_db.py

# Start the server
python main.py
```

The server will start on `http://localhost:10001`

### Docker Quick Start
```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Check logs
docker-compose logs -f mededbot
```

## 📊 System Requirements

### Minimum Requirements
- **Python**: 3.11 or higher
- **Memory**: 2GB RAM
- **Storage**: 1GB for application + space for audio files
- **Database**: PostgreSQL 13+ or Neon.tech account
- **Network**: Stable internet connection for API calls

### Required Services
- **LINE Developer Account**: For messaging platform integration
- **Google Cloud Account**: For Gemini API access
- **Gmail Account**: With app-specific password for email delivery
- **PostgreSQL Database**: Local or cloud (Neon.tech recommended)

### Optional Services
- **Google Drive**: For file backup and storage
- **Docker**: For containerized deployment
- **Synology NAS**: For self-hosted deployment

## 🏗️ Architecture

### High-Level Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   LINE Users    │────▶│  LINE Platform  │────▶│  FastAPI App    │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                        ┌─────────────────────────────────┼─────────────────────────────────┐
                        │                                 │                                 │
                  ┌─────▼──────┐                   ┌──────▼──────┐                  ┌───────▼──────┐
                  │ Gemini 2.5 │                   │ PostgreSQL  │                  │ Google Drive │
                  │  AI + TTS   │                   │  Database   │                  │   Storage    │
                  └────────────┘                   └─────────────┘                  └──────────────┘
```

### Detailed Component Architecture

```mermaid
graph TB
    subgraph "LINE Platform"
        A[LINE User] -->|Text/Voice| B[LINE Messaging API]
    end
    
    subgraph "FastAPI Application"
        B -->|Webhook| C[Webhook Router]
        C --> D[Signature Verification]
        D --> E[Message Handler]
        
        E -->|Text Message| F[Logic Handler]
        E -->|Audio Message| G[Audio Handler]
        
        F -->|Mode Router| H{Mode?}
        H -->|Education| I[Education Handler]
        H -->|Chat| J[MedChat Handler]
        
        G --> K[STT Service]
        K --> F
    end
    
    subgraph "AI Services"
        I --> L[Gemini Service]
        J --> L
        L --> M[TTS Service]
        L --> N[Translation Service]
    end
    
    subgraph "Data Layer"
        O[(PostgreSQL DB)]
        P[Session Manager]
        Q[Google Drive]
        
        E --> P
        L --> O
        M --> Q
    end
    
    subgraph "Output Services"
        R[Email Service]
        S[Static File Server]
        
        I --> R
        M --> S
    end
```

### Core Components

| Component | Description | Key Features | Files |
| **Web Server** | FastAPI async application | HTTPS, health checks, static files | `main.py` |
| **Message Handlers** | Process LINE events | Text, audio, quick replies | `handlers/line_handler.py` |
| **Logic Router** | Mode-based routing | Education vs Chat modes | `handlers/logic_handler.py` |
| **AI Services** | Gemini 2.5 integration | Content generation, translation | `services/gemini_service.py` |
| **Voice Processing** | Audio transcription & synthesis | STT/TTS with multiple voices | `services/stt_service.py`, `tts_service.py` |
| **Data Layer** | PostgreSQL + async operations | Connection pooling, logging | `utils/database.py` |
| **Session Manager** | Thread-safe state management | Expiry, cleanup, persistence | `handlers/session_manager.py` |
| **Email Service** | SMTP with Gmail | HTML formatting, attachments | `utils/email_service.py` |

## 💻 Installation

### Prerequisites Setup

1. **Python 3.11+**
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt install python3.11 python3.11-venv
   
   # macOS with Homebrew
   brew install python@3.11
   
   # Windows - download from python.org
   ```

2. **PostgreSQL Database**
   ```bash
   # Option A: Local PostgreSQL
   sudo apt install postgresql postgresql-contrib
   
   # Option B: Use Neon.tech (recommended)
   # Sign up at https://neon.tech for free cloud database
   ```

3. **Required Accounts**
   - **LINE Developer**: https://developers.line.biz/
   - **Google Cloud**: https://console.cloud.google.com/
   - **Gmail**: Enable 2FA and create app password

### Step-by-Step Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/yourusername/mededbot.git
   cd mededbot
   ```

2. **Create Virtual Environment**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   # Create .env from template
   cp .env.example .env
   
   # Edit with your favorite editor
   nano .env  # or vim, code, etc.
   ```

5. **Set Up Google Credentials**
   ```bash
   # If using Google Drive backup
   # 1. Create service account in Google Cloud Console
   # 2. Download JSON key file
   # 3. Convert to base64:
   base64 -i credentials.json | tr -d '\n' > creds_base64.txt
   # 4. Copy content to GOOGLE_CREDS_B64 in .env
   ```

6. **Initialize Database**
   ```bash
   python init_db.py
   ```

7. **Verify Installation**
   ```bash
   # Run health check
   python -c "from main import app; print('Installation successful!')"
   ```

8. **Start Development Server**
   ```bash
   python main.py
   # Or with uvicorn for auto-reload:
   # uvicorn main:app --reload --host 0.0.0.0 --port 10001
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root with the following structure:

```env
# ===== REQUIRED SETTINGS =====

# Google Gemini AI (get from https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key_here

# LINE Bot Credentials (from LINE Developers Console)
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret

# Database URL (PostgreSQL - use Neon.tech for free cloud DB)
DATABASE_URL=postgresql://user:password@host/database?sslmode=require

# Email Configuration (Gmail with App Password)
GMAIL_ADDRESS=your.email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password

# ===== OPTIONAL SETTINGS =====

# Google Drive Backup (for file storage)
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
GOOGLE_CREDS_B64=base64_encoded_service_account_json

# Server Configuration
BASE_URL=https://your-domain.com  # Required for audio files in production
PORT=10001                         # Default port
LOG_LEVEL=info                     # Options: debug, info, warning, error

# ===== EXAMPLE VALUES =====
# DATABASE_URL=postgresql://user:pass@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
# BASE_URL=https://mededbot.yourdomain.com
```

### Configuration Details

#### 1. Google Gemini API
- Sign up at [Google AI Studio](https://aistudio.google.com/)
- Generate API key from the dashboard
- Enable Gemini 2.5 Flash model access

#### 2. LINE Bot Setup
1. Go to [LINE Developers Console](https://developers.line.biz/)
2. Create new Messaging API channel
3. Basic Settings:
   - Copy Channel Secret → `LINE_CHANNEL_SECRET`
4. Messaging API Settings:
   - Issue Channel Access Token → `LINE_CHANNEL_ACCESS_TOKEN`
   - Set Webhook URL: `https://your-domain.com/webhook`
   - Enable webhook, disable auto-reply

#### 3. Database Setup (Neon.tech)
1. Sign up at [Neon.tech](https://neon.tech/) (free tier available)
2. Create new project
3. Copy connection string → `DATABASE_URL`
4. Ensure `?sslmode=require` is in the URL

#### 4. Gmail App Password
1. Enable 2-factor authentication on Gmail
2. Go to Google Account settings
3. Security → 2-Step Verification → App passwords
4. Generate password for "Mail"
5. Copy 16-character password → `GMAIL_APP_PASSWORD`

#### 5. Google Drive Setup (Optional)
1. Create service account in Google Cloud Console
2. Enable Drive API
3. Share target folder with service account email
4. Download JSON key and convert to base64:
   ```bash
   base64 -i service-account-key.json | tr -d '\n'
   ```

### Security Best Practices

1. **Never commit `.env` to version control**
   ```bash
   # Ensure .env is in .gitignore
   echo ".env" >> .gitignore
   git rm --cached .env  # If accidentally committed
   ```

2. **Use strong passwords and rotate keys regularly**

3. **Restrict database access**
   - Use SSL connections only
   - Limit IP addresses in cloud databases
   - Use read-only credentials where possible

4. **Secure your deployment**
   - Always use HTTPS in production
   - Set up firewall rules
   - Monitor API usage and set alerts

## 📱 Usage Guide

### Command Reference

#### Basic Commands
| Command | Function | Example Usage |
|---------|----------|---------------|
| **new** / **新對話** | Start fresh conversation | User: "new" → Bot: Shows mode selection |
| **衛教** | Education mode | User: "衛教" → Bot: "請輸入醫學主題" |
| **聊天** | Chat mode | User: "聊天" → Bot: Enters Q&A mode |
| **翻譯** | Translate content | User: "翻譯" → Bot: Shows language options |
| **語音** | Generate audio | User: "語音" → Bot: Creates TTS audio |
| **信箱** | Email delivery | User: "信箱" → Bot: "請提供email" |
| **修改** | Modify content | User: "修改" → Bot: "請說明修改需求" |

#### Language Commands
| Language | Commands | Native Name |
|----------|----------|-------------|
| English | en, english, 英文, 英語 | English |
| Japanese | ja, japanese, 日文, 日語 | 日本語 |
| Vietnamese | vi, vietnamese, 越南文 | Tiếng Việt |
| Indonesian | id, indonesian, 印尼文 | Bahasa Indonesia |
| Thai | th, thai, 泰文 | ภาษาไทย |
| Korean | ko, korean, 韓文 | 한국어 |
| Spanish | es, spanish, 西班牙文 | Español |
| French | fr, french, 法文 | Français |
| Tagalog | tl, tagalog, 菲律賓文 | Tagalog |

### Workflow Examples

#### 1. Generate Patient Education Material
```
User: 衛教
Bot: 👋 歡迎使用衛教模式！請輸入想了解的醫學主題...
User: 糖尿病飲食
Bot: [Generates comprehensive patient education about diabetes diet]
     [Shows quick reply: 翻譯 | 語音 | 信箱 | 修改]
```

#### 2. Multilingual Translation
```
User: 翻譯
Bot: 請選擇目標語言 [Shows language quick replies]
User: 越南文
Bot: [Provides Vietnamese translation of the material]
```

#### 3. Voice Interaction Flow
```
User: [Sends voice message in any language]
Bot: 🎙️ 語音訊息處理中...
Bot: 📝 語音內容：[Transcription]
Bot: 🌐 中文翻譯：[Translation]
Bot: [Shows options for further actions]
```

#### 4. Email Delivery
```
User: 信箱
Bot: 📧 請提供您的email地址
User: patient@example.com
Bot: ✅ 已發送到 patient@example.com
```

### Quick Reply Buttons

The bot provides contextual quick reply buttons:

**Mode Selection**
- 🏥 看醫生 衛教 - Health education mode
- 💬 醫療 聊天 - Medical chat mode
- 🎤 語音訊息 - Voice message hint

**Action Buttons**
- 🌐 翻譯 - Translate to another language
- 🔊 語音 - Generate audio version
- 📧 信箱 - Email the content
- ✏️ 修改 - Request modifications
- 🆕 新對話 - Start over

**Language Selection**
- Quick access to top 10 languages
- "顯示更多語言" for full list (100+ languages)

## 🚢 Deployment

### Docker Deployment

#### Quick Start with Docker Compose
```bash
# Clone and configure
git clone https://github.com/yourusername/mededbot.git
cd mededbot
cp .env.example .env
# Edit .env with your credentials

# Build and run
docker-compose up -d

# View logs
docker-compose logs -f mededbot

# Stop
docker-compose down
```

#### Manual Docker Build
```bash
# Build image
docker build -t mededbot:latest .

# Run container
docker run -d \
  --name mededbot \
  -p 10001:10001 \
  --env-file .env \
  -v $(pwd)/tts_audio:/app/tts_audio \
  -v $(pwd)/voicemail:/app/voicemail \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  mededbot:latest
```

### Production Deployment Options

#### Option 1: VPS Deployment (DigitalOcean, Linode, AWS EC2)
```bash
# 1. SSH to your server
ssh user@your-server-ip

# 2. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# 3. Clone and configure
git clone https://github.com/yourusername/mededbot.git
cd mededbot
cp .env.example .env
nano .env  # Add your credentials

# 4. Run with Docker Compose
docker-compose up -d

# 5. Set up reverse proxy (nginx)
sudo apt install nginx
sudo nano /etc/nginx/sites-available/mededbot
```

**Nginx Configuration**:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:10001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Option 2: Synology NAS Deployment
```bash
# Use the Synology-specific compose file
docker-compose -f docker-compose.synology.yml up -d
```

See [SYNOLOGY_DEPLOYMENT.md](markdowns/SYNOLOGY_DEPLOYMENT.md) for detailed instructions.

#### Option 3: Cloud Platform Deployment

**Render.com**:
1. Fork this repository
2. Connect GitHub to Render
3. Create new Web Service
4. Set environment variables
5. Deploy (auto-builds on push)

**Railway.app**:
1. Install Railway CLI: `npm i -g @railway/cli`
2. Login: `railway login`
3. Initialize: `railway init`
4. Add variables: `railway variables set`
5. Deploy: `railway up`

**Google Cloud Run**:
```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT-ID/mededbot

# Deploy to Cloud Run
gcloud run deploy mededbot \
  --image gcr.io/PROJECT-ID/mededbot \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated
```

### Production Checklist

#### Pre-deployment
- [ ] Remove `.env` from repository
- [ ] Set strong passwords for all services
- [ ] Configure firewall rules
- [ ] Set up SSL certificates

#### LINE Configuration
- [ ] Webhook URL: `https://your-domain.com/webhook`
- [ ] Webhook enabled, auto-reply disabled
- [ ] Verify webhook in LINE console

#### Environment Setup
- [ ] All API keys configured in `.env`
- [ ] Database connection tested
- [ ] Email sending verified
- [ ] Google Drive folder shared (if using)

#### Post-deployment
- [ ] Test health endpoint: `https://your-domain.com/ping`
- [ ] Send test message in LINE
- [ ] Verify TTS audio playback
- [ ] Check database logging
- [ ] Monitor error logs

## 📚 API Reference

### REST Endpoints

#### 1. Root Health Check
```http
GET /
HEAD /

Response: 200 OK
{
  "message": "✅ FastAPI LINE + Gemini bot is running.",
  "status": "Online",
  "endpoints": ["/", "/chat", "/ping", "/webhook"]
}
```

#### 2. Simple Health Check
```http
GET /ping
HEAD /ping

Response: 200 OK
{
  "status": "ok"
}
```

#### 3. LINE Webhook
```http
POST /webhook
Headers:
  X-Line-Signature: {webhook_signature}
  Content-Type: application/json

Body: LINE webhook events

Response: 200 OK
"OK"
```

#### 4. Test Chat Endpoint
```http
POST /chat
Content-Type: application/json

{
  "message": "糖尿病的飲食建議"
}

Response: 200 OK
{
  "reply": "[AI generated response about diabetes diet]"
}
```

#### 5. Static File Server
```http
GET /static/{filename}

Example: GET /static/U1234567890_1234567890.wav
Response: Audio file with proper MIME type
```

### WebSocket Support
Not currently implemented. All communication is via HTTP REST.

### Rate Limiting
- No built-in rate limiting
- Recommended: Use reverse proxy (nginx) or API gateway
- LINE platform has its own rate limits

### Error Responses
```json
// 400 Bad Request
{
  "detail": "Invalid signature"
}

// 404 Not Found
{
  "detail": "Not Found"
}

// 500 Internal Server Error
{
  "detail": "Internal server error"
}
```

## 🗄️ Database Schema

### Tables Structure

#### 1. chat_logs
```sql
CREATE TABLE chat_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(255) NOT NULL,
    message TEXT,
    reply TEXT,
    action_type VARCHAR(100),
    gemini_call BOOLEAN DEFAULT FALSE,
    gemini_output_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_logs_user_id ON chat_logs(user_id);
CREATE INDEX idx_chat_logs_timestamp ON chat_logs(timestamp);
```

#### 2. tts_logs
```sql
CREATE TABLE tts_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(255) NOT NULL,
    text TEXT,
    audio_filename VARCHAR(255),
    audio_url TEXT,
    drive_link TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tts_logs_user_id ON tts_logs(user_id);
```

#### 3. voicemail_logs
```sql
CREATE TABLE voicemail_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(255) NOT NULL,
    audio_filename VARCHAR(255),
    transcription TEXT,
    translation TEXT,
    drive_link TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_voicemail_logs_user_id ON voicemail_logs(user_id);
```

### Data Types
- **user_id**: LINE user ID (U + 32 hex characters)
- **action_type**: 'edu', 'chat', 'translate', 'tts', 'email', etc.
- **status**: 'success', 'failed', 'processing'
- **timestamps**: UTC timezone

### Database Maintenance
```sql
-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Clean old logs (older than 90 days)
DELETE FROM chat_logs WHERE timestamp < NOW() - INTERVAL '90 days';
DELETE FROM tts_logs WHERE timestamp < NOW() - INTERVAL '90 days';
DELETE FROM voicemail_logs WHERE timestamp < NOW() - INTERVAL '90 days';
```

## 🔧 Project Structure

```
mededbot/
├── main.py                 # FastAPI application entry point
├── init_db.py             # Database initialization script
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
├── docker-compose.yml    # Docker services orchestration
├── docker-compose.synology.yml  # Synology NAS specific
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
│
├── handlers/             # Request handlers
│   ├── __init__.py
│   ├── line_handler.py   # LINE message processing
│   ├── logic_handler.py  # Core business logic
│   ├── mail_handler.py   # Email functionality
│   ├── medchat_handler.py # Medical chat mode
│   └── session_manager.py # User session management
│
├── services/             # External service integrations
│   ├── __init__.py
│   ├── gemini_service.py # Google Gemini AI integration
│   ├── stt_service.py    # Speech-to-text service
│   ├── tts_service.py    # Text-to-speech service
│   └── prompt_config.py  # AI prompt templates
│
├── utils/                # Utility modules
│   ├── __init__.py
│   ├── database.py       # Database operations
│   ├── email_service.py  # Email sending utilities
│   ├── google_drive_service.py # File upload utilities
│   ├── logging.py        # Logging configuration
│   ├── command_sets.py   # Command recognition sets
│   ├── paths.py          # Path configurations
│   └── retry_utils.py    # Retry logic decorators
│
├── routes/               # API routes
│   ├── __init__.py
│   └── webhook.py        # LINE webhook endpoint
│
├── sql/                  # Database schemas
│   ├── create_tables.sql # Table definitions
│   └── fix_sequences.sql # Sequence fixes
│
├── markdowns/            # Documentation
│   ├── DEPLOYMENT.md     # Deployment guide
│   ├── SYNOLOGY_DEPLOYMENT.md # Synology guide
│   ├── MIGRATION_GUIDE.md # Migration instructions
│   └── TTS_SYNOLOGY_TROUBLESHOOTING.md
│
├── tts_audio/            # Generated TTS audio files
├── voicemail/            # Voice message files
└── logs/                 # Application logs
```

## 🔐 Security

### Security Features

1. **Authentication & Authorization**
   - LINE webhook signature verification
   - User ID validation for all requests
   - No public endpoints without authentication

2. **Data Protection**
   - SSL/TLS required for database connections
   - Encrypted credential storage
   - Secure session management with expiry

3. **Input Validation**
   - File size limits (10MB for audio)
   - Email address validation
   - Command injection prevention
   - Path traversal protection

4. **Container Security**
   - Non-root user in Docker
   - Minimal Alpine Linux base
   - No unnecessary packages

### Security Checklist

- [ ] Never commit `.env` or credentials
- [ ] Use HTTPS in production
- [ ] Rotate API keys regularly
- [ ] Monitor for unusual activity
- [ ] Keep dependencies updated
- [ ] Use firewall rules
- [ ] Enable database SSL
- [ ] Implement rate limiting

### Vulnerability Reporting

If you discover a security vulnerability:
1. Do NOT open a public issue
2. Email security concerns to [your-email]
3. Include detailed reproduction steps
4. Allow 48 hours for initial response

## 🐛 Troubleshooting

### Common Issues and Solutions

#### 1. Bot Not Responding
```bash
# Check if server is running
curl http://localhost:10001/ping

# Check Docker logs
docker-compose logs -f mededbot

# Verify webhook URL
curl -X POST https://your-domain.com/webhook
```

**Solutions**:
- Verify LINE webhook URL is correct
- Check `X-Line-Signature` validation
- Ensure port 10001 is not blocked
- Confirm `.env` variables are loaded

#### 2. Audio Files Not Playing
**Symptoms**: TTS generates file but LINE shows error

**Checklist**:
- [ ] `BASE_URL` in `.env` uses HTTPS
- [ ] URL is publicly accessible
- [ ] File permissions: `chmod 644 tts_audio/*.wav`
- [ ] Nginx serves `/static` path correctly

**Test**:
```bash
# Test audio URL directly
curl -I https://your-domain.com/static/test.wav
```

#### 3. Database Connection Failed
**Error**: `connection to server at "host" (...), port 5432 failed`

**Solutions**:
```bash
# Test connection
python -c "from utils.database import init_db; import asyncio; asyncio.run(init_db())"

# Check DATABASE_URL format
echo $DATABASE_URL
# Should be: postgresql://user:pass@host/db?sslmode=require
```

#### 4. Gemini API Errors
**Error**: `429 Resource Exhausted` or timeout

**Solutions**:
- Check API quotas in Google Cloud Console
- Implement exponential backoff
- Reduce request frequency
- Verify API key is valid

#### 5. Email Delivery Failed
**Error**: `SMTPAuthenticationError`

**Solutions**:
1. Enable 2FA on Gmail
2. Generate app-specific password
3. Check firewall allows port 587
4. Verify `GMAIL_APP_PASSWORD` is 16 characters

#### 6. Voice Message Processing Failed
**Error**: Audio download or transcription fails

**Debug Steps**:
```python
# Check file size
ls -lh voicemail/

# Test STT manually
python -c "from services.stt_service import transcribe_audio; print(transcribe_audio('test.m4a'))"
```

### Debug Mode

Enable detailed logging:
```bash
# In .env
LOG_LEVEL=debug

# Or in docker-compose.yml
environment:
  - LOG_LEVEL=debug
```

### Log Analysis

```bash
# View recent errors
docker-compose logs mededbot | grep ERROR

# Monitor in real-time
docker-compose logs -f mededbot

# Check specific handler
docker-compose logs mededbot | grep "\[WEBHOOK\]"
```

### Performance Issues

If bot responds slowly:
1. Check database query performance
2. Monitor Gemini API response times
3. Verify adequate server resources
4. Consider implementing caching

### Getting Help

1. Check existing issues on GitHub
2. Review logs for error details
3. Include in bug reports:
   - Error messages
   - Steps to reproduce
   - Environment details
   - Relevant logs

See [TTS_SYNOLOGY_TROUBLESHOOTING.md](markdowns/TTS_SYNOLOGY_TROUBLESHOOTING.md) for Synology-specific issues.

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

### How to Contribute

1. **Fork the Repository**
   ```bash
   git clone https://github.com/yourusername/mededbot.git
   cd mededbot
   git remote add upstream https://github.com/original/mededbot.git
   ```

2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Your Changes**
   - Write clean, documented code
   - Follow existing patterns
   - Add tests if applicable

4. **Test Your Changes**
   ```bash
   # Run locally
   python main.py
   
   # Test with Docker
   docker-compose up --build
   ```

5. **Commit and Push**
   ```bash
   git add .
   git commit -m "feat: add amazing new feature"
   git push origin feature/your-feature-name
   ```

6. **Open a Pull Request**
   - Describe your changes
   - Reference any related issues
   - Wait for review

### Development Guidelines

#### Code Style
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use meaningful variable names

#### Commit Messages
Follow conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

#### Testing
- Add tests for new features
- Ensure existing tests pass
- Test edge cases
- Document test scenarios

#### Documentation
- Update README for new features
- Add docstrings to functions
- Include usage examples
- Update API documentation

### Areas for Contribution

- **Language Support**: Add more languages or improve translations
- **Medical Content**: Enhance medical accuracy with expert input
- **Features**: Implement roadmap items or propose new ones
- **Bug Fixes**: Help fix reported issues
- **Documentation**: Improve guides and examples
- **Testing**: Add test coverage
- **Performance**: Optimize slow operations
- **Security**: Identify and fix vulnerabilities

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 MedEdBot Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 🙏 Acknowledgments

### Special Thanks To

- **Google Gemini Team** - For providing advanced AI capabilities
- **LINE Corporation** - For the reliable messaging platform
- **Healthcare Professionals** - For invaluable feedback and testing
- **Open Source Community** - For the amazing tools and libraries

### Technologies Used

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database toolkit
- [LINE Bot SDK](https://github.com/line/line-bot-sdk-python) - LINE integration
- [Google Generative AI](https://ai.google.dev/) - Gemini AI SDK
- [Docker](https://www.docker.com/) - Containerization
- [PostgreSQL](https://www.postgresql.org/) - Database
- [Neon](https://neon.tech/) - Serverless Postgres

## 📞 Support

### Getting Help

- **Documentation**: Check the [docs](markdowns/) folder
- **Issues**: [Open an issue](https://github.com/yourusername/mededbot/issues)
- **Discussions**: Join our [discussions](https://github.com/yourusername/mededbot/discussions)
- **Email**: contact@mededbot.example.com

### Community

- Follow updates on [Twitter/X](https://twitter.com/mededbot)
- Join our [Discord server](https://discord.gg/mededbot)
- Read our [blog](https://blog.mededbot.example.com)

## 🚀 Roadmap

### Current Version: 1.0.0

### Planned Features

#### Version 1.1 (Q2 2024)
- [ ] Multi-modal medical image analysis
- [ ] Offline mode for basic functions
- [ ] Batch processing for multiple patients
- [ ] Export to PDF functionality

#### Version 1.2 (Q3 2024)
- [ ] Integration with hospital systems
- [ ] Advanced symptom checker
- [ ] Medication interaction warnings
- [ ] Clinical decision support

#### Version 2.0 (Q4 2024)
- [ ] Healthcare provider dashboard
- [ ] Analytics and insights
- [ ] Multi-platform support (WhatsApp, Telegram)
- [ ] Plugin system for extensions

### Known Limitations

- Audio files require manual cleanup
- Sessions are memory-based (lost on restart)
- Limited to LINE platform currently
- No real-time collaboration features

---

<p align="center">
  <strong>MedEdBot - Breaking Language Barriers in Healthcare</strong><br>
  Made with ❤️ for healthcare professionals worldwide<br>
  <a href="#-quick-start">Get Started</a> •
  <a href="#-contributing">Contribute</a> •
  <a href="#-support">Get Help</a>
</p>