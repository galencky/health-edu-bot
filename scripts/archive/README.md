# Archived Scripts

These scripts were used for the Google Drive to Cloudflare R2 migration (July 2025).

## Directory Structure

### migration/
Scripts used to migrate data from Google Drive to Cloudflare R2:
- `sync_drive_to_r2.py` - Initial sync from Drive to R2
- `update_db_urls_to_r2.py` - Update database URLs from Drive to R2
- `apply_url_mapping.py` - Apply URL mappings to database

### verification/
Scripts used to verify the migration:
- `verify_url_mapping.py` - Verify URL mappings between local files and database
- `check_db_urls.py` - Check current database URL status

### analysis/
Scripts for analyzing data:
- `check_audio_formats.py` - Check audio file formats in database

### fixes/
Scripts to fix issues found during migration:
- `fix_incorrect_r2_urls.py` - Fix R2 URLs that used wrong domain
- `simple_url_fix.py` - Simple URL fix based on local files as ground truth

## Migration Summary

The migration moved file storage from Google Drive to Cloudflare R2 with:
- Custom domain: https://galenchen.uk
- UTF-8 encoding for text files
- Maintained file naming patterns:
  - Text files: `{user_id}-{timestamp}.txt` in `/text/` directory
  - WAV files: `{user_id}_{timestamp}.wav` in `/tts_audio/` directory
  - M4A files: `{user_id}_{timestamp}.m4a` in `/voicemail/` directory