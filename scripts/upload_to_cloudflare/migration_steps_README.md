# Step-by-Step Google Drive to Cloudflare R2 Migration

This is a three-step process to migrate files from Google Drive to Cloudflare R2.

## Overview

1. **Step 1**: Download all files from Google Drive to local storage
2. **Step 2**: Upload downloaded files to Cloudflare R2
3. **Step 3**: Update database records with new R2 URLs

## Prerequisites

### Python Dependencies
```bash
pip install google-api-python-client google-auth boto3 asyncpg sqlalchemy python-dotenv
```

### Environment Variables
Add these to your `.env` file:

```env
# Database
DATABASE_URL=postgresql://user:pass@host/db

# Google Drive (for Step 1) - Use either option:
# Option 1: Base64-encoded credentials
GOOGLE_CREDS_B64=your-base64-encoded-json-here

# Option 2: Path to service account file
GOOGLE_SERVICE_ACCOUNT_FILE=path/to/service-account-key.json

# Cloudflare R2 (for Step 2)
R2_ENDPOINT_URL=https://[account-id].r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your-access-key-id
R2_SECRET_ACCESS_KEY=your-secret-access-key
R2_BUCKET_NAME=your-bucket-name
R2_PUBLIC_URL=https://your-r2-public-url.com
```

### Google Service Account Setup

#### Option 1: Using Base64-encoded credentials (Recommended)
1. If you have the credentials in base64 format, add to .env:
   ```
   GOOGLE_CREDS_B64=ewogICJ0eXBlIjog...
   ```

#### Option 2: Using service account file
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new service account or use existing
3. Download the JSON key file
4. Enable Google Drive API
5. Share your Google Drive folder with the service account email
6. Add to .env:
   ```
   GOOGLE_SERVICE_ACCOUNT_FILE=path/to/service-account-key.json
   ```

### Cloudflare R2 Setup
1. Create an R2 bucket in Cloudflare dashboard
2. Generate API tokens with read/write permissions
3. Set up public access if needed (for serving files)

## Step 1: Download from Google Drive

```bash
python scripts/step1_download_from_drive.py
```

### What it does:
- Queries database for all Google Drive links
- Downloads files using Google Drive API
- Organizes files locally in `C:\Users\galen\Downloads\mededbot_drive`:
  ```
  C:\Users\galen\Downloads\mededbot_drive\
  ├── chat_logs\
  │   └── {user_id}\
  │       ├── {timestamp}_gemini_output_{id}.html
  │       └── metadata.csv
  ├── tts_audio\
  │   └── {user_id}\
  │       ├── {timestamp}_{filename}.wav
  │       └── metadata.csv
  └── voicemail\
      └── {user_id}\
          ├── {timestamp}_{filename}.m4a
          └── metadata.csv
  ```
- Creates metadata.csv for each user with file information
- Tracks failed downloads in `failed_downloads.csv`

### Features:
- Resume support (skips already downloaded files)
- Progress indication for large files
- Detailed logging
- Preserves original filenames where available

### Output:
- Downloaded files in `C:\Users\galen\Downloads\mededbot_drive\` directory
- Metadata files for tracking
- Summary statistics

## Step 2: Upload to Cloudflare R2

```bash
python scripts/step2_upload_to_r2.py
```

### What it does:
- Reads files from `C:\Users\galen\Downloads\mededbot_drive\` directory
- Uploads each file to Cloudflare R2
- Maintains same directory structure in R2:
  ```
  bucket/
  ├── chat_logs/{user_id}/{timestamp}_gemini_output_{id}.html
  ├── tts_audio/{user_id}/{timestamp}_{filename}.wav
  └── voicemail/{user_id}/{timestamp}_{filename}.m4a
  ```
- Creates `r2_upload_log.csv` with upload details

### Features:
- Automatic content-type detection
- Skip already uploaded files
- Progress tracking
- Preserves file organization

### Output:
- Files uploaded to R2
- `r2_upload_log.csv` with mapping of files to R2 URLs

## Step 3: Update Database

```bash
python scripts/step3_update_database.py
```

### What it does:
- Reads `r2_upload_log.csv` from Step 2
- Updates database records:
  - `chat_logs.gemini_output_url`
  - `tts_logs.drive_link`
  - `voicemail_logs.drive_link`
- Creates detailed update log

### Features:
- Confirmation prompt before updating
- Detailed progress display
- Success/failure tracking
- Update log with old and new URLs

### Output:
- Updated database records
- `database_update_log_{timestamp}.csv` with all changes

## Verification

After completing all steps, you can verify:

1. **Check a few URLs manually**:
   - Open some R2 URLs in browser
   - Ensure files are accessible

2. **Query database**:
   ```sql
   -- Check remaining Google Drive links
   SELECT COUNT(*) FROM chat_logs 
   WHERE gemini_output_url LIKE '%drive.google.com%';
   
   SELECT COUNT(*) FROM tts_logs 
   WHERE drive_link LIKE '%drive.google.com%';
   
   SELECT COUNT(*) FROM voicemail_logs 
   WHERE drive_link LIKE '%drive.google.com%';
   ```

3. **Review logs**:
   - Check `failed_downloads.csv` for any download failures
   - Check `database_update_log_*.csv` for update status

## Handling Failures

### Download Failures (Step 1)
- Check `failed_downloads.csv`
- Common issues:
  - File deleted from Drive
  - Permission issues
  - Invalid file ID

### Upload Failures (Step 2)
- Re-run Step 2 (it skips already uploaded files)
- Check R2 credentials
- Verify bucket exists and has proper permissions

### Database Update Failures (Step 3)
- Check update log for specific errors
- Can be re-run safely (updates are idempotent)

## Post-Migration

1. **Update Application Code**:
   - Modify upload logic to use R2 instead of Google Drive
   - Update any hardcoded Drive URLs

2. **Backup Considerations**:
   - Keep `C:\Users\galen\Downloads\mededbot_drive\` directory as backup
   - Consider archiving to cold storage

3. **Cleanup**:
   - After verification, can delete local downloads:
     ```cmd
     rmdir /s /q "C:\Users\galen\Downloads\mededbot_drive"
     ```
   - Archive log files for future reference

## Troubleshooting

### "Service account file not found"
- Ensure `GOOGLE_SERVICE_ACCOUNT_FILE` path is correct
- Check file permissions

### "Access denied" from Google Drive
- Verify Drive folder is shared with service account email
- Check service account has Drive API enabled

### "Invalid endpoint" from R2
- Verify `R2_ENDPOINT_URL` format
- Should be: `https://[account-id].r2.cloudflarestorage.com`

### Database connection errors
- Verify `DATABASE_URL` is correct
- Check network connectivity to database

## Notes

- Process is resumable at any step
- Each step produces logs for troubleshooting
- Files are organized by user_id for easy management
- Original timestamps are preserved in filenames