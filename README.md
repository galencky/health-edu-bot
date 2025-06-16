# MedEdBot - Medical Education & Communication LINE Bot

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![LINE](https://img.shields.io/badge/LINE-Messaging_API-00C300.svg)](https://developers.line.biz/en/services/messaging-api/)

A bilingual medical education and communication bot for LINE, powered by Google Gemini AI. Designed to bridge language barriers in healthcare settings and provide accurate patient education materials.

## 🌟 Key Features

### 📚 Education Mode
- **Patient Education Materials**: Generate comprehensive, medically accurate education sheets
- **Multi-language Support**: Automatic translation to 20+ languages
- **Content Modification**: Fine-tune generated content with specific instructions
- **Email Delivery**: Send education materials directly to patients' email
- **Web Search Integration**: Automatically includes credible medical references

### 💬 Medical Chat Mode
- **Real-time Medical Translation**: Facilitate doctor-patient communication across language barriers
- **Context-aware Translation**: Maintains medical terminology accuracy
- **Quick Reply Interface**: Streamlined user experience with button-based interactions

### 🎙️ Voice Support
- **Speech-to-Text (STT)**: Transcribe voice messages using Google Gemini
- **Voice Translation**: Translate transcribed audio to any language
- **Text-to-Speech (TTS)**: Generate natural voice output for translations
- **Supported Languages**: Chinese, English, Japanese, Korean, Thai, Vietnamese, and more

### 🔒 Security & Reliability
- **Rate Limiting**: 30 req/min for AI, 20 req/min for TTS per user
- **Circuit Breaker**: Automatic failure recovery for external services
- **Input Validation**: Comprehensive sanitization and security checks
- **Session Management**: 24-hour expiry with automatic cleanup
- **Graceful Degradation**: Service remains operational during partial failures

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    LINE     │────▶│   FastAPI   │────▶│   Gemini    │
│   Users     │     │   Server    │     │     AI      │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────┼──────┐
                    │      │      │
              ┌─────▼──┐ ┌─▼──┐ ┌▼──────────┐
              │ Postgre│ │Drive│ │   Email    │
              │   SQL   │ │API  │ │  Service   │
              └────────┘ └────┘ └───────────┘
```

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL database
- LINE Messaging API account
- Google Cloud account with Gemini API access
- Gmail account with app password
- Google Drive API credentials (optional)

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/mededbot.git
cd mededbot
```

### 2. Environment Setup
```bash
cp .env.template .env
# Edit .env with your credentials
```

### 3. Required Environment Variables
```env
# Database
DATABASE_URL=postgresql://user:pass@host/dbname

# LINE Bot
LINE_CHANNEL_ACCESS_TOKEN=your_line_token
LINE_CHANNEL_SECRET=your_line_secret

# Google Gemini AI
GEMINI_API_KEY=your_gemini_api_key

# Email Service
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password

# Google Drive (Optional)
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
GOOGLE_CREDS_B64=base64_encoded_service_account_json

# Deployment
BASE_URL=https://your-domain.com
PORT=8080  # Use 8080 for cloud, 10001 for local
USE_MEMORY_STORAGE=true  # true for cloud, false for persistent
```

### 4. Docker Deployment
```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### 5. Local Development
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Run server
uvicorn main:app --host 0.0.0.0 --port 10001 --reload
```

## 💬 Usage Guide

### Starting a Conversation
1. Add the bot as a friend on LINE
2. Send "new" or "開始" to begin
3. Choose between Education (衛教) or Chat (聊天) mode

### Education Mode Commands
- **Generate**: `disease name + topic` (e.g., "糖尿病 飲食控制")
- **Modify**: Click "✏️ 修改" button
- **Translate**: Click "🌐 翻譯" button
- **Email**: Click "📧 寄送" button
- **New**: Click "🆕 新對話" button

### Chat Mode Flow
1. Select target language
2. Type or speak your message
3. Receive translation with pronunciation guide

### Voice Features
1. Send voice message
2. Bot transcribes and shows original text
3. Choose translation language or click "new" to skip
4. Optionally generate voice output with "🔊 朗讀" button

## 🔧 Configuration

### Storage Modes
- **Memory Mode** (`USE_MEMORY_STORAGE=true`): For serverless/cloud deployments
- **Disk Mode** (`USE_MEMORY_STORAGE=false`): For persistent server deployments

### Timeout Settings
- Webhook timeout: 48 seconds
- Gemini API timeout: 45 seconds with 2 retries
- Health check: Every 120s with 50s timeout

### Rate Limits
- Gemini API: 30 requests/minute per user
- TTS: 20 requests/minute per user
- Email: 5 requests/minute per user

## 📊 Database Schema

### Tables
- `chat_logs`: All message interactions
- `tts_logs`: Text-to-speech generation logs
- `voicemail_logs`: Voice message transcriptions

## 🛡️ Security Features

- LINE webhook signature verification
- Input sanitization for all user inputs
- Path traversal protection
- Email validation with MX record checking
- Secure file handling with size limits
- No storage of sensitive medical data

## 🔍 Monitoring

### Health Check Endpoint
```bash
curl https://your-domain.com/health
```

### Log Monitoring
```bash
# Docker logs
docker-compose logs -f | grep -E "(ERROR|TIMEOUT|GEMINI)"

# System logs
tail -f logs/app.log
```

## 🐛 Troubleshooting

### Common Issues

1. **502 Bad Gateway**
   - Check Gemini API key validity
   - Verify timeout settings
   - Review Docker memory limits

2. **AI Service Timeout**
   - Extend timeouts in `gemini_service.py`
   - Check circuit breaker status
   - Monitor API rate limits

3. **Voice Features Not Working**
   - Verify audio file permissions
   - Check storage mode configuration
   - Ensure BASE_URL is correctly set

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 🙏 Acknowledgments

- Google Gemini AI for powerful language models
- LINE Corporation for messaging platform
- FastAPI for high-performance web framework
- PostgreSQL for reliable data storage

## 📧 Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/mededbot/issues)
- Email: support@your-domain.com

---

**Note**: This bot is designed for educational purposes and should not replace professional medical consultation. Always verify medical information with qualified healthcare providers.