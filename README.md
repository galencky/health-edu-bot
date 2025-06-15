# MedEdBot - Medical Education LINE Chatbot

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![LINE](https://img.shields.io/badge/LINE-Messaging_API-00C300.svg)](https://developers.line.biz/en/services/messaging-api/)

A multilingual medical education chatbot for LINE messaging platform, powered by Google Gemini AI.

## Features

- 🎓 **Dual Mode Operation**: Education mode for browsing materials, Medical chat mode for Q&A
- 🎙️ **Voice Support**: Speech-to-text and text-to-speech capabilities
- 🌏 **Multilingual**: Supports Chinese, English, Japanese, and many others.
- 📧 **Email Integration**: Send educational content directly to email
- 🔒 **Secure**: Input validation, rate limiting, and LINE signature verification
- 📊 **Analytics**: Comprehensive logging of all interactions

## Quick Start

### Prerequisites

- Docker and Docker Compose
- LINE Messaging API credentials
- Google Cloud credentials (Gemini API, Service Account)
- PostgreSQL database

### Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mededbot.git
cd mededbot
```

2. Create `.env` file from template:
```bash
cp .env.template .env
```

3. Fill in your credentials in `.env`

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  mededbot:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Container Image

The Docker image is optimized for production:
- Based on `python:3.11-alpine` for minimal size
- Multi-stage build for security
- Non-root user execution
- Health check endpoint included

### Building the Image

```bash
# Build locally
docker build -t mededbot:latest .

# Build with specific tag
docker build -t mededbot:v1.0.0 .
```

### Running the Container

```bash
# Run with environment file
docker run -d --name mededbot \
  --env-file .env \
  -p 8000:8000 \
  mededbot:latest

# Run with individual environment variables
docker run -d --name mededbot \
  -e GEMINI_API_KEY=your_key \
  -e LINE_CHANNEL_ACCESS_TOKEN=your_token \
  -p 8000:8000 \
  mededbot:latest
```

## Architecture

- **Backend**: FastAPI with async/await support
- **AI**: Google Gemini for content generation and translation
- **Database**: PostgreSQL for logging and analytics
- **Storage**: Adaptive (memory for cloud, disk for persistent environments)
- **Deployment**: Optimized for Render.com, Synology NAS, and cloud platforms

## API Endpoints

- `POST /`: LINE webhook endpoint
- `GET /health`: Health check endpoint
- `GET /`: Welcome page

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Run with uvicorn
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## Security

- All credentials must be set via environment variables
- LINE signature verification on all webhooks
- Input validation and sanitization
- Rate limiting to prevent abuse
- Session isolation for multi-user support

## Performance Optimization

- Minimal Alpine Linux base image
- Multi-stage Docker build
- In-memory storage for ephemeral environments
- Efficient session management
- Async I/O throughout

## Monitoring

- Comprehensive logging to PostgreSQL
- Health check endpoint for uptime monitoring
- Detailed error tracking and reporting

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and feature requests, please use the GitHub issue tracker.