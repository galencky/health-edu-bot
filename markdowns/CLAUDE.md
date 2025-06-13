# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MedEdBot is a multilingual medical education and translation chatbot for healthcare professionals in Taiwan. It integrates with LINE messaging and uses Google Gemini AI to help medical staff communicate with patients across language barriers.

## Development Commands

### Setup & Run
```bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run locally with auto-reload
uvicorn main:app --host 0.0.0.0 --port 10000 --reload

# Build and run with Docker
docker build -t mededbot .
docker run -p 10001:10001 mededbot
```

### Testing Endpoints
```bash
# Health check
curl http://localhost:10000/

# Test without LINE integration
curl -X POST http://localhost:10000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

## Architecture & Flow

The application follows a layered architecture:

1. **Entry Point**: `main.py` - FastAPI application with webhook endpoint
2. **Request Flow**: 
   - LINE webhook → `routes/webhook.py` → `handlers/line_handler.py`
   - Line handler extracts message → `handlers/logic_handler.py` for routing
   - Logic handler determines mode (education/chat) and calls appropriate services

3. **Core Components**:
   - **Session Management**: `handlers/session_manager.py` stores user states in memory
   - **AI Integration**: `services/gemini_service.py` handles all Gemini API calls
   - **Audio Processing**: `services/stt_service.py` (speech-to-text) and `services/tts_service.py` (text-to-speech)
   - **External Services**: Google Drive/Sheets logging, email delivery via SMTP

4. **Key Modes**:
   - **Health Education ("衛教")**: Generate multilingual patient education sheets
   - **MedChat**: Real-time medical translation with TTS support
   - **Voicemail**: Transcribe and translate voice messages

## Important Implementation Details

### Environment Variables
Required in `.env` file:
- LINE API credentials: `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_CHANNEL_SECRET`
- Google services: `GEMINI_API_KEY`, `GOOGLE_CREDS_B64`, `GOOGLE_DRIVE_FOLDER_ID`
- Database: `CONNECTION_STRING` (Neon PostgreSQL connection string)
- Email: `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`
- Server: `BASE_URL` (for serving TTS audio files)

### State Management
- User sessions are stored in-memory in `SessionManager` class
- Sessions track: current mode, language preference, conversation history
- No persistence layer - sessions are lost on restart

### File Handling
- TTS audio files: Saved to `tts_audio/` directory, served via `/static/{filename}`
- Voicemail files: Saved to `voicemail/` directory
- All interactions logged to Neon PostgreSQL database
- Audio files and Gemini logs uploaded to Google Drive for storage

### LINE Integration
- Uses LINE Flex Messages for rich UI (buttons, carousels)
- Handles text messages, audio messages, and postback events
- Quick reply buttons for common actions

### AI Prompts
- Medical prompt templates in `services/prompt_config.py`
- Emphasizes medical accuracy and appropriate disclaimers
- Supports multiple languages with native speaker quality translation

## Current Development Branch

Working on `dev-features/google-search-tts` - adding Google Search integration and enhanced TTS capabilities.