"""
Cloudflare R2 service for file storage
Replaces Google Drive functionality with R2 storage
"""
import os
import io
import boto3
import asyncio
from datetime import datetime
from botocore.config import Config
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple, Dict
import mimetypes

# Thread pool for async operations
_r2_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="r2-upload-")

class R2Service:
    """Cloudflare R2 service for file uploads"""
    
    def __init__(self):
        self.endpoint_url = os.getenv('R2_ENDPOINT_URL')
        self.access_key = os.getenv('R2_ACCESS_KEY_ID')
        self.secret_key = os.getenv('R2_SECRET_ACCESS_KEY')
        self.bucket_name = os.getenv('R2_BUCKET_NAME', 'mededbot')
        # Always use custom domain for public URLs
        self.public_url = 'https://galenchen.uk'
        
        if not all([self.endpoint_url, self.access_key, self.secret_key]):
            raise ValueError("R2 credentials not configured. Please set R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY")
        
        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(
                signature_version='s3v4',
                region_name='auto'
            )
        )
    
    def get_content_type(self, filename: str) -> str:
        """Get content type with proper charset for text files"""
        content_type, _ = mimetypes.guess_type(filename)
        
        if not content_type:
            ext = os.path.splitext(filename)[1].lower()
            content_type_map = {
                '.wav': 'audio/wav',
                '.mp3': 'audio/mpeg',
                '.m4a': 'audio/mp4',
                '.aac': 'audio/aac',
                '.html': 'text/html; charset=utf-8',
                '.htm': 'text/html; charset=utf-8',
                '.txt': 'text/plain; charset=utf-8',
                '.pdf': 'application/pdf',
                '.json': 'application/json; charset=utf-8',
                '.xml': 'text/xml; charset=utf-8'
            }
            content_type = content_type_map.get(ext, 'application/octet-stream')
        else:
            # Add UTF-8 charset for text files
            if content_type.startswith('text/') and 'charset' not in content_type:
                content_type += '; charset=utf-8'
        
        return content_type
    
    def upload_file(self, file_data: bytes, key: str, content_type: Optional[str] = None) -> Dict[str, str]:
        """
        Upload file to R2
        Returns dict with 'id' and 'webViewLink' for compatibility
        """
        if not content_type:
            content_type = self.get_content_type(key)
        
        try:
            # Additional headers
            extra_args = {
                'ContentType': content_type
            }
            
            # Add cache control for text files
            if content_type.startswith('text/'):
                extra_args['CacheControl'] = 'no-cache'
            
            # Upload to R2
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_data,
                **extra_args
            )
            
            # Return compatible format
            public_url = f"{self.public_url}/{key}"
            return {
                'id': key,
                'webViewLink': public_url
            }
            
        except ClientError as e:
            print(f"[R2] Upload failed for {key}: {e}")
            raise
    
    def upload_text_file(self, content: str, filename: str, folder: str = "text") -> Dict[str, str]:
        """Upload text content as UTF-8 encoded file"""
        # Ensure content is UTF-8 encoded
        file_data = content.encode('utf-8')
        
        # Create key with folder structure (no timestamp prefix - it's already in filename)
        key = f"{folder}/{filename}"
        
        return self.upload_file(file_data, key, content_type='text/plain; charset=utf-8')
    
    def upload_audio_file(self, audio_data: bytes, filename: str, folder: str = "audio") -> Dict[str, str]:
        """Upload audio file"""
        # Create key with folder structure
        key = f"{folder}/{filename}"
        
        return self.upload_file(audio_data, key)
    
    def upload_gemini_output(self, content: str, user_id: str, session_data: dict) -> Tuple[str, str]:
        """Upload Gemini output as text file matching existing format"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create text content matching existing format
        input_message = session_data.get('last_user_message', 'N/A')
        
        # Format content to match existing structure
        text_content = f"""Timestamp: {timestamp}
User ID: {user_id}
Input Message: {input_message}

Gemini zh_output:
{content}"""
        
        # Upload to R2 - matching existing format
        # Format: text/{user_id}/{user_id}-{timestamp}.txt
        filename = f"{user_id}-{timestamp}.txt"
        result = self.upload_text_file(text_content, filename, folder=f"text/{user_id}")
        
        return result['webViewLink'], result['id']


# Singleton instance
_r2_service = None

def get_r2_service() -> R2Service:
    """Get or create R2 service instance"""
    global _r2_service
    if _r2_service is None:
        _r2_service = R2Service()
    return _r2_service


# Async wrappers for compatibility
async def upload_to_r2_async(file_data: bytes, key: str, content_type: Optional[str] = None) -> Dict[str, str]:
    """Async wrapper for R2 upload"""
    loop = asyncio.get_event_loop()
    service = get_r2_service()
    return await loop.run_in_executor(
        _r2_executor,
        service.upload_file,
        file_data,
        key,
        content_type
    )


async def upload_gemini_log_async(user_id: str, session: dict, message: str) -> Tuple[str, str]:
    """Async wrapper for Gemini log upload"""
    loop = asyncio.get_event_loop()
    service = get_r2_service()
    
    # Get the Gemini output from session
    gemini_output = session.get('gemini_output', '')
    if not gemini_output:
        gemini_output = session.get('last_bot_message', 'No output available')
    
    # Store message in session for metadata
    session['last_user_message'] = message
    
    return await loop.run_in_executor(
        _r2_executor,
        service.upload_gemini_output,
        gemini_output,
        user_id,
        session
    )


# Compatibility function to match google_drive_service interface
def upload_gemini_log(user_id: str, session: dict, message: str) -> Tuple[str, str]:
    """Sync wrapper for Gemini log upload (matches google_drive_service interface)"""
    service = get_r2_service()
    
    # Get the Gemini output from session
    gemini_output = session.get('gemini_output', '')
    if not gemini_output:
        gemini_output = session.get('last_bot_message', 'No output available')
    
    # Store message in session for metadata
    session['last_user_message'] = message
    
    return service.upload_gemini_output(gemini_output, user_id, session)