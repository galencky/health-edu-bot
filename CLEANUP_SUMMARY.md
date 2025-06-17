# Code Cleanup Summary

## Services Directory

### Removed from `tts_service.py`:
- `list_available_models()` function - Debug function that was never called

### Removed from `prompt_config.py`:
- `voicemail_prompt` - Unused prompt template

## Utils Directory

### Simplified `circuit_breaker.py`:
- Removed `acall()` async method - Never used
- Removed `get_status()` method - Never used
- Removed `drive_circuit_breaker` - Never used
- Removed `line_api_circuit_breaker` - Never used
- Kept only the `gemini_circuit_breaker` that's actually used

### Removed from `retry_utils.py`:
- `retry_with_timeout()` function - Never used

### Removed from `rate_limiter.py`:
- `email_limiter` - Never used
- `webhook_limiter` - Never used
- Kept `cleanup_old_entries()` with a note that it should be called periodically

## Not Changed (Require Careful Analysis)

### `database.py`:
- Has duplicate `get_db_session_sync()` functions but needs careful analysis to consolidate
- Multiple engine functions that may have different purposes

### `memory_storage.py`:
- `get_info()` method is unused but might be useful for debugging

### `storage_config.py`:
- Complex cloud detection logic could be simplified but works correctly

## Result
- Removed ~200 lines of unused code
- Simplified circuit breaker from 156 lines to 109 lines
- Code is now cleaner without losing any functionality