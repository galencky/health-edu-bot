-- SQL script to create MedEdBot logging tables in Neon database
-- Run this in your Neon SQL editor or psql

-- Create chat_logs table
CREATE TABLE IF NOT EXISTS chat_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    message TEXT,
    reply TEXT,
    action_type VARCHAR(100),
    gemini_call BOOLEAN DEFAULT FALSE,
    gemini_output_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create TTS logs table  
CREATE TABLE IF NOT EXISTS tts_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    text TEXT,
    audio_filename VARCHAR(255),
    audio_url TEXT,
    drive_link TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create voicemail logs table
CREATE TABLE IF NOT EXISTS voicemail_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    audio_filename VARCHAR(255),
    transcription TEXT,
    translation TEXT,
    drive_link TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chat_logs_user_id ON chat_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_logs_timestamp ON chat_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_tts_logs_user_id ON tts_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_tts_logs_timestamp ON tts_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_voicemail_logs_user_id ON voicemail_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_voicemail_logs_timestamp ON voicemail_logs(timestamp);

-- Verify tables were created
SELECT 'chat_logs' as table_name, COUNT(*) as row_count FROM chat_logs
UNION ALL
SELECT 'tts_logs' as table_name, COUNT(*) as row_count FROM tts_logs  
UNION ALL
SELECT 'voicemail_logs' as table_name, COUNT(*) as row_count FROM voicemail_logs;

-- Show table structures
\d chat_logs;
\d tts_logs;
\d voicemail_logs;