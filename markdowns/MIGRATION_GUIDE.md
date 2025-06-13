# Database Logging Migration Guide

This guide explains the new Neon database logging system that replaces Google Sheets logging.

## Overview

The logging system has been completely migrated to use Neon PostgreSQL database. Google Sheets logging has been removed, while Google Drive is still used for file storage (audio files, Gemini logs).

## New Features

1. **Database-Only Logging**: All logs are now written directly to Neon PostgreSQL
2. **Three Log Types**:
   - `chat_logs`: General chat interactions and Gemini API calls
   - `tts_logs`: Text-to-speech generation logs
   - `voicemail_logs`: Voice message transcriptions

## Setup Instructions

### 1. Add Database Connection String

Add your Neon database connection string to your `.env` file:

```bash
CONNECTION_STRING=postgresql://user:password@host.neon.tech/database?sslmode=require
```

### 2. Install Dependencies

Install the new database dependencies:

```bash
pip install -r requirements.txt
```

### 3. Initialize Database Tables

Run the initialization script to create the required tables:

```bash
python init_db.py
```

This will create three tables:
- `chat_logs`
- `tts_logs`
- `voicemail_logs`

## Database Schema

### chat_logs
- `id`: Primary key
- `timestamp`: When the interaction occurred
- `user_id`: LINE user ID
- `message`: User's message
- `reply`: Bot's reply (truncated to 1000 chars)
- `action_type`: Type of action performed
- `gemini_call`: Boolean indicating if Gemini was called
- `gemini_output_url`: Link to detailed Gemini output in Drive
- `created_at`: Record creation timestamp

### tts_logs
- `id`: Primary key
- `timestamp`: When TTS was generated
- `user_id`: LINE user ID
- `text`: Text converted to speech (truncated to 1000 chars)
- `audio_filename`: Name of generated audio file
- `audio_url`: Public URL to access audio
- `drive_link`: Google Drive link to audio file
- `status`: Generation status
- `created_at`: Record creation timestamp

### voicemail_logs
- `id`: Primary key
- `timestamp`: When voicemail was processed
- `user_id`: LINE user ID
- `audio_filename`: Original audio filename
- `transcription`: STT transcription result
- `translation`: Translation result (if requested)
- `drive_link`: Google Drive link to audio file
- `created_at`: Record creation timestamp

## Production Deployment

### Environment Variables

Ensure these environment variables are set in production:

```bash
# Required for database logging
CONNECTION_STRING=postgresql://...

# Still required for Google Drive file storage
GOOGLE_CREDS_B64=...
GOOGLE_DRIVE_FOLDER_ID=...
```

### Docker Deployment

The Dockerfile already includes all necessary dependencies. Just rebuild:

```bash
docker build -t mededbot .
docker run -p 10001:10001 --env-file .env mededbot
```

## Monitoring

### Query Examples

Check recent chat logs:
```sql
SELECT * FROM chat_logs 
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
```

Check TTS usage by user:
```sql
SELECT user_id, COUNT(*) as tts_count 
FROM tts_logs 
GROUP BY user_id 
ORDER BY tts_count DESC;
```

Check voicemail transcriptions:
```sql
SELECT * FROM voicemail_logs 
WHERE transcription IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;
```

## Removed Components

The following files have been removed as they are no longer needed:
- `utils/log_to_sheets.py` - Google Sheets logging
- `utils/tts_log.py` - TTS Google Sheets logging
- `utils/google_sheets.py` - Google Sheets client
- `utils/voicemail_drive.py` - Voicemail Drive upload (integrated into logging.py)

Dependencies removed:
- `gspread` - Google Sheets API
- `oauth2client` - OAuth for Google Sheets

## Future Considerations

1. Add indexes for better query performance:
   ```sql
   CREATE INDEX idx_chat_logs_user_id ON chat_logs(user_id);
   CREATE INDEX idx_chat_logs_created_at ON chat_logs(created_at);
   CREATE INDEX idx_tts_logs_user_id ON tts_logs(user_id);
   CREATE INDEX idx_voicemail_logs_user_id ON voicemail_logs(user_id);
   ```

2. Set up regular backups of your Neon database
3. Consider implementing log retention policies
4. Monitor database size and performance
5. Consider adding more detailed analytics queries