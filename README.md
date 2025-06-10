# MedEdBot 🏥🤖

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![LINE Bot](https://img.shields.io/badge/LINE-Bot_SDK-00C300.svg)](https://developers.line.biz/)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini_AI-4285F4.svg)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A multilingual medical education and translation chatbot for healthcare professionals in Taiwan. MedEdBot integrates with LINE messaging and leverages Google's Gemini AI to bridge language barriers in medical settings, providing instant translations, patient education materials, and voice message transcription in multiple languages.

## 🌟 Key Features

- **Real-time Medical Translation**: Instant translation between Mandarin, English, Japanese, and more
- **Voice Message Processing**: Transcribe and translate voice messages with high accuracy
- **Patient Education Sheets**: Generate multilingual patient education materials on-demand
- **Text-to-Speech**: Convert translated text to natural-sounding audio for better communication
- **Google Search Integration**: Access up-to-date medical information when needed
- **Session Management**: Maintain conversation context across interactions
- **Comprehensive Logging**: Track all interactions with PostgreSQL database and Google Drive backup

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Deployment](#-deployment)
- [API Reference](#-api-reference)
- [Contributing](#-contributing)

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/MedEdBot.git
cd MedEdBot

# Set up environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your credentials

# Initialize database
python init_db.py

# Run the application
uvicorn main:app --host 0.0.0.0 --port 10000 --reload
```

## 🏗️ Architecture

### System Architecture

```mermaid
graph TD
    A[LINE User] -->|Message/Audio| B[LINE Platform]
    B -->|Webhook| C[FastAPI Server]
    C --> D[Line Handler]
    D --> E[Logic Handler]
    E -->|Education Mode| F[Education Handler]
    E -->|Chat Mode| G[MedChat Handler]
    E -->|Voice Message| H[STT Service]
    F --> I[Gemini AI]
    G --> I
    H --> I
    I --> J[TTS Service]
    I --> K[Email Service]
    C --> L[(PostgreSQL)]
    C --> M[Google Drive]
    J --> N[Audio Files]
    K --> O[Gmail SMTP]
```

### Core Components

| Component | Description | Key Files |
|-----------|-------------|-----------|
| **Web Server** | FastAPI application handling LINE webhooks | `main.py` |
| **Message Handlers** | Process different types of user interactions | `handlers/` |
| **AI Services** | Gemini integration for translation & generation | `services/gemini_service.py` |
| **Audio Processing** | Speech-to-text and text-to-speech | `services/stt_service.py`, `services/tts_service.py` |
| **Data Persistence** | PostgreSQL logging & Google Drive backup | `utils/database.py` |
| **Session Management** | In-memory user state tracking | `handlers/session_manager.py` |

## 💻 Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL database (or Neon account)
- LINE Developer account
- Google Cloud account with Gemini API access
- Google service account for Drive/Sheets
- Gmail account with app password

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/MedEdBot.git
   cd MedEdBot
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
   # Edit .env with your credentials
   ```

5. **Initialize database**
   ```bash
   python init_db.py
   ```

6. **Run the application**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 10000 --reload
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://user:pass@host/db?ssl=require

# LINE Bot
LINE_CHANNEL_ACCESS_TOKEN=your_token
LINE_CHANNEL_SECRET=your_secret

# Google AI
GEMINI_API_KEY=your_gemini_api_key

# Email
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password

# Google Drive
GOOGLE_DRIVE_FOLDER_ID=folder_id
GOOGLE_CREDS_B64=base64_encoded_credentials

# Server (important for audio playback)
BASE_URL=https://your-public-domain.com
```

### Google Service Account Setup

1. Create a service account in Google Cloud Console
2. Enable Google Drive and Sheets APIs
3. Download JSON credentials
4. Convert to base64: `base64 -i credentials.json`
5. Add to `GOOGLE_CREDS_B64` in `.env`

### LINE Bot Configuration

1. Create a Messaging API channel in [LINE Developers Console](https://developers.line.biz/)
2. Set webhook URL: `https://your-domain.com/webhook`
3. Copy channel access token and secret to `.env`

## 📱 Usage

### LINE Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| **衛教** | Start health education mode | "衛教" → Select condition → Get multilingual sheet |
| **中文/英文** | Switch chat language | "英文" → Switch to English |
| **Voice messages** | Auto-transcribe & translate | Send audio → Get transcript |

### Quick Reply Buttons

The bot provides contextual quick reply buttons for common actions:
- Language selection (中文/English/日本語)
- Common medical conditions
- Email delivery options
- Mode switching

## 🚢 Deployment

### Docker Deployment

```bash
# Build and run with Docker
docker build -t mededbot .
docker run -p 10001:10001 \
  --env-file .env \
  -v $(pwd)/tts_audio:/app/tts_audio \
  -v $(pwd)/voicemail:/app/voicemail \
  mededbot
```

### Synology NAS Deployment

```bash
# Use the Synology-specific compose file
docker-compose -f docker-compose.synology.yml up -d
```

See [SYNOLOGY_DEPLOYMENT.md](SYNOLOGY_DEPLOYMENT.md) for detailed instructions.

### Cloud Deployment (Render/Railway)

1. Connect your GitHub repository
2. Set environment variables in dashboard
3. Deploy with automatic builds

### Production Checklist

- [ ] HTTPS configured (required for LINE audio)
- [ ] Database migrations completed
- [ ] Environment variables set
- [ ] Public URL accessible
- [ ] Webhook URL updated in LINE console
- [ ] Google Drive folder shared with service account
- [ ] Email app password configured

## 📚 API Reference

### REST Endpoints

#### Health Check
```http
GET /
```
Returns server status and metadata.

#### LINE Webhook
```http
POST /webhook
X-Line-Signature: {signature}
```
Handles LINE platform events.

#### Test Chat
```http
POST /chat
Content-Type: application/json

{
  "message": "Hello"
}
```

### Static Files
```http
GET /static/{filename}
```
Serves TTS audio files.

## 🗄️ Database Schema

```sql
CREATE TABLE IF NOT EXISTS interaction_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(50),
    user_message TEXT,
    bot_response TEXT,
    mode VARCHAR(20),
    language VARCHAR(20),
    extras JSONB,
    error TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 Project Structure

```
MedEdBot/
├── main.py                    # FastAPI application
├── requirements.txt           # Dependencies
├── Dockerfile                 # Container configuration
├── docker-compose.yml         # Docker orchestration
├── init_db.py                 # Database setup
├── .env.example              # Environment template
│
├── handlers/                  # Request handlers
│   ├── line_handler.py       # LINE message processing
│   ├── logic_handler.py      # Business logic routing
│   ├── medchat_handler.py    # Medical chat mode
│   ├── mail_handler.py       # Email functionality
│   └── session_manager.py    # User sessions
│
├── services/                  # External services
│   ├── gemini_service.py     # Google Gemini AI
│   ├── stt_service.py        # Speech-to-text
│   ├── tts_service.py        # Text-to-speech
│   └── prompt_config.py      # AI prompts
│
├── utils/                     # Utilities
│   ├── database.py           # Database operations
│   ├── logging.py            # Structured logging
│   ├── google_drive_service.py # File backup
│   ├── email_service.py      # SMTP client
│   └── command_sets.py       # Command recognition
│
└── routes/                    # API routes
    └── webhook.py            # LINE webhook
```

## 🔐 Security

- Environment variables stored securely in `.env`
- LINE webhook signature validation
- Input sanitization and validation
- Non-root Docker container
- SSL/TLS database connections
- Secure file handling with size limits

## 🐛 Troubleshooting

### Common Issues

1. **Audio not playing in LINE**
   - Check `BASE_URL` is publicly accessible
   - Ensure HTTPS is configured
   - Verify file permissions

2. **Database connection errors**
   - Verify `DATABASE_URL` format
   - Check SSL requirements
   - Test connection with `init_db.py`

3. **Google Drive upload failures**
   - Verify service account credentials
   - Check folder permissions
   - Ensure folder ID is correct

4. **LINE webhook not receiving messages**
   - Verify webhook URL in LINE console
   - Check signature validation
   - Review server logs

See [troubleshooting guide](TTS_SYNOLOGY_TROUBLESHOOTING.md) for detailed solutions.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Keep commits atomic and descriptive

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Google Gemini team for the powerful AI models
- LINE Corporation for the messaging platform
- Healthcare professionals who provided feedback
- Open source community for the amazing tools

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check existing documentation
- Review logs for error details

---

<p align="center">Made with ❤️ for healthcare professionals in Taiwan</p>