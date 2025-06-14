-- Fix PostgreSQL sequences after table recreation
-- This resets all sequences to be greater than the current max ID in each table

-- Fix chat_logs sequence
DO $$
DECLARE
    max_id INTEGER;
BEGIN
    -- Get the current max ID from chat_logs table
    SELECT COALESCE(MAX(id), 0) INTO max_id FROM chat_logs;
    
    -- Reset the sequence to max_id + 1
    EXECUTE format('ALTER SEQUENCE chat_logs_id_seq RESTART WITH %s', max_id + 1);
    
    RAISE NOTICE 'chat_logs_id_seq reset to %', max_id + 1;
END $$;

-- Fix tts_logs sequence
DO $$
DECLARE
    max_id INTEGER;
BEGIN
    -- Get the current max ID from tts_logs table
    SELECT COALESCE(MAX(id), 0) INTO max_id FROM tts_logs;
    
    -- Reset the sequence to max_id + 1
    EXECUTE format('ALTER SEQUENCE tts_logs_id_seq RESTART WITH %s', max_id + 1);
    
    RAISE NOTICE 'tts_logs_id_seq reset to %', max_id + 1;
END $$;

-- Verify the fixes
SELECT 
    'chat_logs' as table_name,
    (SELECT MAX(id) FROM chat_logs) as max_id,
    (SELECT last_value FROM chat_logs_id_seq) as sequence_value
UNION ALL
SELECT 
    'tts_logs' as table_name,
    (SELECT MAX(id) FROM tts_logs) as max_id,
    (SELECT last_value FROM tts_logs_id_seq) as sequence_value