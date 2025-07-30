# Cloudflare R2 Migration Summary

This document summarizes the changes made to migrate from Google Drive to Cloudflare R2 for file storage.

## Changes Made

### 1. New R2 Service Module (`utils/r2_service.py`)
- Created a new service module that handles all R2 operations
- Maintains compatibility with the old Google Drive interface
- Automatically sets UTF-8 encoding for text files
- Supports audio file uploads with proper content types

### 2. Updated Logging Module (`utils/logging.py`)
- Replaced Google Drive imports with R2 service imports
- Updated `_upload_audio_file()` to use R2
- Updated `_async_log_chat()` to use R2 for Gemini logs
- Maintained all existing functionality

### 3. Updated Storage Configuration (`utils/storage_config.py`)
- Replaced `GOOGLE_DRIVE` backend with `R2`
- Updated detection logic to check for R2 credentials
- Added `TTS_USE_R2` flag

### 4. Environment Variables

#### Old (Google Drive):
```env
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
GOOGLE_CREDS_B64=base64_encoded_credentials
```

#### New (Cloudflare R2):
```env
R2_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your_access_key_id
R2_SECRET_ACCESS_KEY=your_secret_access_key
R2_BUCKET_NAME=mededbot
R2_PUBLIC_URL=https://your-domain.com
```

## File Organization in R2

Files are organized with the following structure:
```
bucket/
├── gemini/{user_id}/         # Gemini AI outputs (HTML)
├── tts_audio/{user_id}/      # TTS audio files
├── voicemail/{user_id}/      # Voicemail recordings
└── text/                     # Other text files
```

## Key Features

### 1. UTF-8 Encoding
All text files (`.txt`, `.html`, `.json`) are automatically served with `charset=utf-8` to ensure proper display of Chinese characters in browsers.

### 2. Content Types
The system automatically detects and sets appropriate content types:
- `.wav` → `audio/wav`
- `.mp3` → `audio/mpeg`
- `.m4a` → `audio/mp4`
- `.html` → `text/html; charset=utf-8`
- `.txt` → `text/plain; charset=utf-8`

### 3. Public URLs
Files are accessible via your custom domain:
- Format: `https://your-domain.com/{category}/{user_id}/{filename}`
- Example: `https://galenchen.uk/text/U123/20250725_gemini.html`

### 4. Backward Compatibility
The R2 service maintains the same interface as the Google Drive service, returning dictionaries with:
- `id`: The R2 object key
- `webViewLink`: The public URL

## Migration Steps for Existing Deployments

1. **Set up Cloudflare R2**:
   - Create an R2 bucket
   - Generate API credentials
   - Configure public access or custom domain

2. **Update Environment Variables**:
   - Remove Google Drive variables
   - Add R2 configuration variables

3. **Deploy Updated Code**:
   - The system will automatically detect R2 configuration
   - New uploads will go to R2
   - Old Google Drive links will continue to work

4. **Optional: Migrate Existing Files**:
   - Use the migration scripts in `scripts/` folder
   - This will copy files from Google Drive to R2
   - Update database links to point to R2

## Testing

To test the R2 integration:
1. Send a message that triggers Gemini AI
2. Check that the response includes an R2 link
3. Click the link to verify UTF-8 encoding works
4. Send a voice message to test audio uploads

## Troubleshooting

### "R2 service not configured"
Ensure all R2 environment variables are set correctly.

### Chinese characters appear garbled
The system automatically sets UTF-8 encoding. If issues persist, check your R2 bucket's CORS configuration.

### Upload failures
Check that your R2 credentials have write permissions and the bucket exists.

## Benefits of R2 over Google Drive

1. **Simpler Authentication**: No complex service accounts or OAuth
2. **Better Performance**: CDN-backed delivery
3. **Custom Domains**: Use your own domain for file URLs
4. **Cost Effective**: Generous free tier and predictable pricing
5. **S3 Compatible**: Industry-standard API