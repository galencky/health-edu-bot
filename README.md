# MedEdBot - Multilingual Medical Education & Translation Chatbot

**A LINE-based healthcare communication assistant powered by Google Gemini AI**

**Author:** Kuan-Yuan Chen, M.D.  
**Contact:** galen147258369@gmail.com  
**License:** MIT

---

## 🎯 Project Overview

MedEdBot is an AI-powered LINE chatbot designed to bridge language barriers in healthcare settings. Built specifically for medical professionals in Taiwan, it provides instant multilingual patient education materials and real-time medical translation services directly through LINE - the most widely used messaging platform in Taiwan.

### Key Problems Solved

1. **Language Barriers in Healthcare**: Medical staff often struggle to communicate with patients who speak different languages
2. **Time-Consuming Education Material Creation**: Doctors spend significant time creating and translating patient education sheets
3. **Limited Access to Professional Medical Translation**: Real-time, accurate medical translation is expensive and often unavailable
4. **Technology Restrictions**: Hospital IT policies often block external apps, but LINE is universally accessible

### Core Features

- **🏥 Health Education Sheets ("衛教")**: Generate structured patient education materials in Traditional Chinese, with instant translation to 24+ languages
- **💬 MedChat Real-time Translation**: Live medical conversation translation with context awareness
- **🎙️ Voice Message Processing**: Transcribe and translate LINE voice messages using Gemini's speech-to-text
- **🔊 Text-to-Speech (TTS)**: Generate natural-sounding audio in multiple languages for patients who cannot read
- **📧 Multi-channel Delivery**: Send materials via LINE or email with full formatting preserved
- **📊 Comprehensive Logging**: All interactions logged to Google Drive/Sheets for quality assurance and analytics

---

## 🏗️ System Architecture

### High-Level Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────┐
│    LINE     │────▶│   FastAPI App   │────▶│  Google Gemini   │
│   Client    │◀────│   (main.py)     │◀────│      API         │
└─────────────┘     └────────┬────────┘     └──────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
              ┌─────▼─────┐    ┌─────▼─────┐
              │  Google   │    │   Gmail   │
              │Drive/Sheets│    │   SMTP    │
              └───────────┘    └───────────┘
```

### Component Architecture

```
main.py (FastAPI Application)
│
├── routes/
│   └── webhook.py          → LINE webhook endpoint handler
│
├── handlers/               → Request processing layer
│   ├── line_handler.py     → LINE message/audio event processing
│   ├── logic_handler.py    → Core business logic & mode routing
│   ├── session_manager.py  → Thread-safe user session management
│   ├── medchat_handler.py  → Real-time translation logic
│   └── mail_handler.py     → Email composition & delivery
│
├── services/               → External service integrations
│   ├── gemini_service.py   → Gemini API wrapper with Google Search
│   ├── prompt_config.py    → System prompts for different modes
│   ├── stt_service.py      → Speech-to-text via Gemini
│   └── tts_service.py      → Text-to-speech via Gemini
│
└── utils/                  → Helper functions
    ├── command_sets.py     → Multi-language command recognition
    ├── email_service.py    → SMTP email helper
    ├── google_drive_service.py → Drive upload with caching
    ├── google_sheets.py    → Sheets API wrapper
    ├── log_to_sheets.py    → Interaction logging
    ├── paths.py            → Thread-safe directory management
    ├── tts_log.py          → TTS logging pipeline
    └── voicemail_drive.py  → Voice message archival
```

### Data Flow

1. **Incoming Message**: LINE → Webhook → Handler → Session Manager
2. **Content Generation**: Logic Handler → Gemini Service → Google Search (optional)
3. **Response**: Handler → LINE API (text/audio/flex messages)
4. **Logging**: Parallel upload to Google Drive & Sheets

---

## 🔧 Technical Implementation Details

### Session Management

- **Thread-Safe Design**: Uses `threading.Lock` for synchronous contexts and `asyncio.Lock` for async operations
- **Automatic Expiration**: Sessions expire after 24 hours of inactivity
- **Memory Efficient**: Background cleanup task runs hourly
- **State Tracking**: Maintains user mode, language preferences, content history

```python
# Session structure
{
    "started": bool,
    "mode": "edu" | "chat" | None,
    "zh_output": str,              # Chinese content
    "translated_output": str,      # Translated content
    "references": List[Dict],      # Google Search references
    "chat_target_lang": str,       # MedChat target language
    "awaiting_*": bool,            # Various state flags
    ...
}
```

### Google Gemini Integration

#### Models Used

- **Content Generation**: `gemini-2.5-flash-preview-05-20` with Google Search tool
- **Text-to-Speech**: `gemini-2.5-flash-preview-tts` (dedicated TTS model)
- **Speech-to-Text**: Via Gemini Files API

#### Advanced Features

1. **Web Search Integration**: Automatic reference extraction from search results
2. **Timeout Protection**: 30-second timeout on all API calls
3. **Error Recovery**: Graceful degradation on API failures
4. **Response Caching**: Stores last response for reference extraction

### Security & Reliability

1. **Input Validation**
   - Email header injection protection
   - File size limits (10MB for audio)
   - Path traversal prevention for static files

2. **Resource Management**
   - Automatic file cleanup after processing
   - File descriptor leak prevention
   - Proper context managers for all I/O

3. **Error Handling**
   - Comprehensive try-catch blocks
   - User-friendly error messages
   - Detailed logging for debugging

### LINE Integration

#### Message Types Supported

- **Text Messages**: Commands and content input
- **Audio Messages**: Voice transcription and translation
- **Flex Messages**: Interactive UI with buttons and references

#### Rich UI Components

```python
# Example Flex Message for references
{
    "type": "bubble",
    "body": {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {"type": "text", "text": "參考來源", "weight": "bold"},
            {"type": "text", "text": title, "color": "#3366CC", 
             "action": {"type": "uri", "uri": url}}
        ]
    }
}
```

### Multi-language Support

- **Command Recognition**: Supports English, Chinese, and mixed commands
- **Content Languages**: 24 languages via Gemini (auto-detected)
- **TTS Voices**: 30 voice options with different styles
- **UI Languages**: Traditional Chinese with English fallbacks

---

## 📋 Configuration & Setup

### Prerequisites

- Python 3.9+
- LINE Messaging API Channel
- Google Cloud Service Account
- Gmail with App Password
- Public HTTPS endpoint (for webhooks)

### Environment Variables

Create a `.env` file with:

```bash
# LINE API Credentials
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token
LINE_CHANNEL_SECRET=your_channel_secret

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key

# Email Configuration
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password

# Google Cloud Services
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id
GOOGLE_CREDS_B64=base64_encoded_service_account_json

# Server Configuration
BASE_URL=https://your-domain.com  # For TTS audio URLs
PORT=10001  # Optional, defaults to 10001
```

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/mededbot.git
cd mededbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --host 0.0.0.0 --port 10001 --reload
```

### LINE Webhook Setup

1. Set webhook URL in LINE Developer Console: `https://your-domain.com/webhook`
2. Enable webhook and disable auto-reply
3. Add bot as friend using QR code

---

## 💡 Usage Guide

### Basic Workflow

1. **Start Session**: Send "new" or "開始"
2. **Choose Mode**:
   - "ed" / "衛教" → Education mode
   - "chat" / "聊天" → Translation mode

### Education Mode ("衛教")

```
User: 糖尿病飲食控制
Bot: [Generates comprehensive education sheet with references]
     
Commands:
- "modify" → Edit content
- "translate" → Translate to another language  
- "mail" → Send via email
- "speak" → Generate audio (after translation)
```

### MedChat Mode

```
User: chat
Bot: 請輸入欲翻譯的語言
User: English
Bot: Ready for translation
User: 病人說肚子很痛
Bot: The patient says their stomach hurts a lot
```

### Voice Messages

1. Send audio message → Automatic transcription
2. Choose language or type "無" to skip translation
3. Optional: Generate TTS of translation

---

## 🔍 Advanced Features

### Google Search Integration

- Automatic web search for current medical information
- Reference extraction with titles and URLs
- Accumulative reference list across modifications

### Session Persistence

- Content preserved across interactions
- References accumulate through workflow
- Clean display without repetition

### Logging & Analytics

All interactions logged with:
- Timestamp
- User ID
- Input/Output content
- Gemini API usage
- Session state
- Error tracking

### Performance Optimizations

1. **Caching**: Google Drive service cached to reduce I/O
2. **Concurrent Processing**: Async operations where possible
3. **Resource Pooling**: Connection reuse for external services
4. **Smart Chunking**: LINE message limits handled automatically

---

## 🛠️ Development & Extension

### Adding New Commands

Edit `utils/command_sets.py`:

```python
new_feature_commands = {
    "feature", "功能", "특징"  # English, Chinese, Korean
}
```

### Custom Prompts

Modify `services/prompt_config.py` for different output styles or medical specialties.

### Adding Languages

1. Update command sets
2. Test with Gemini (auto-detects from 24 supported languages)
3. Add UI translations if needed

### Deployment Options

1. **Docker**: Dockerfile included for containerization
2. **Cloud Run**: Auto-scaling with Google Cloud
3. **Traditional VPS**: Use systemd service with nginx

---

## 🚨 Troubleshooting

### Common Issues

1. **TTS Fails**: Check BASE_URL is publicly accessible
2. **Session Lost**: Normal after 24 hours or server restart
3. **References Missing**: Ensure content requires web search
4. **Email Delivery**: Verify Gmail app password and less secure apps

### Debug Mode

Enable debug logging:
```python
# In handlers/logic_handler.py
print(f"[DEBUG] Session state: {session}")
```

### Health Checks

- `GET /` - System status and endpoints
- `GET /ping` - Simple connectivity test
- `POST /chat` - Test without LINE

---

## 📈 Performance & Scaling

### Current Limitations

- In-memory sessions (lost on restart)
- Single-process architecture
- 10MB audio file limit
- 5000 character TTS limit

### Scaling Recommendations

1. **Redis**: For distributed session storage
2. **Cloud Storage**: For audio files instead of local disk
3. **Load Balancer**: For multiple instances
4. **CDN**: For static audio delivery

---

## 🔒 Security Considerations

### Implemented Protections

- SQL injection: N/A (no SQL database)
- XSS: HTML escaping for user inputs
- Path traversal: Static file serving restricted
- File upload: Size limits and type validation
- Email injection: Header validation
- Rate limiting: Via LINE platform

### Best Practices

1. Never commit `.env` file
2. Rotate API keys regularly
3. Monitor Google Cloud usage
4. Review logs for anomalies
5. Keep dependencies updated

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/NewFeature`)
3. Commit changes (`git commit -m 'Add NewFeature'`)
4. Push to branch (`git push origin feature/NewFeature`)
5. Open Pull Request

### Code Style

- Python: Follow PEP 8
- Comments: English for code, Chinese for medical terms
- Docstrings: Required for public functions
- Type hints: Encouraged for clarity

---

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 🙏 Acknowledgments

- Google Gemini team for the powerful AI models
- LINE Corporation for the messaging platform
- Taiwan medical community for feedback and testing
- Open source contributors

---

**For medical professionals seeking to improve patient communication across language barriers**

*Developed with ❤️ by Dr. Kuan-Yuan Chen*