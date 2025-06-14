"""Input validation utilities for security"""
import re
import os
from typing import Optional
import unicodedata

# Security constants
MAX_USER_ID_LENGTH = 50
MAX_MESSAGE_LENGTH = 5000
MAX_FILENAME_LENGTH = 255
MAX_EMAIL_LENGTH = 254
ALLOWED_AUDIO_EXTENSIONS = {'.wav', '.m4a', '.mp3', '.ogg'}

def sanitize_user_id(user_id: str) -> str:
    """Sanitize and validate LINE user ID"""
    if not user_id:
        raise ValueError("User ID cannot be empty")
    
    # LINE user IDs start with 'U' followed by 32 hex characters
    if not re.match(r'^U[0-9a-fA-F]{32}$', user_id):
        raise ValueError("Invalid LINE user ID format")
    
    return user_id

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks"""
    if not filename:
        raise ValueError("Filename cannot be empty")
    
    # Remove any path components
    filename = os.path.basename(filename)
    
    # Remove dangerous characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = re.sub(r'\.+', '.', filename)  # Prevent multiple dots
    
    # Normalize unicode
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # Limit length
    if len(filename) > MAX_FILENAME_LENGTH:
        name, ext = os.path.splitext(filename)
        filename = name[:MAX_FILENAME_LENGTH - len(ext)] + ext
    
    # Ensure it's not empty after sanitization
    if not filename or filename == '.':
        raise ValueError("Invalid filename after sanitization")
    
    return filename

def validate_email(email: str) -> str:
    """Validate and sanitize email address"""
    if not email:
        raise ValueError("Email cannot be empty")
    
    # Basic email regex (RFC 5322 simplified)
    email_pattern = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    email = email.strip().lower()
    
    if len(email) > MAX_EMAIL_LENGTH:
        raise ValueError(f"Email too long (max {MAX_EMAIL_LENGTH} characters)")
    
    if not email_pattern.match(email):
        raise ValueError("Invalid email format")
    
    # Prevent email header injection
    if any(char in email for char in ['\n', '\r', '\0']):
        raise ValueError("Invalid characters in email")
    
    return email

def sanitize_text(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    """Sanitize user input text"""
    if not text:
        return ""
    
    # Remove null bytes and control characters
    text = text.replace('\0', '')
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()

def validate_language_code(lang_code: str) -> str:
    """Validate language code format"""
    if not lang_code:
        raise ValueError("Language code cannot be empty")
    
    # Allow common formats: en, en-US, chinese, etc.
    if not re.match(r'^[a-zA-Z]{2,20}(-[a-zA-Z]{2,20})?$', lang_code):
        raise ValueError("Invalid language code format")
    
    return lang_code.lower()

def validate_audio_filename(filename: str) -> str:
    """Validate audio filename"""
    filename = sanitize_filename(filename)
    
    # Check extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise ValueError(f"Invalid audio file extension. Allowed: {ALLOWED_AUDIO_EXTENSIONS}")
    
    return filename

def validate_action_type(action_type: Optional[str]) -> Optional[str]:
    """Validate action type for logging"""
    if not action_type:
        return None
    
    original_action = action_type
    allowed_actions = {
        'edu', 'chat', 'translate', 'tts', 'email', 
        'modify', 'voicemail', 'new', 'help', 'other',
        'sync reply', 'medchat_audio', 'gemini reply', 'medchat', 
        'exception', 'audio', 'text', 'voice',
        'speak', 'medchat audio'  # Additional variants
    }
    
    action_type = action_type.lower().strip()
    
    if action_type not in allowed_actions:
        print(f"🔍 [VALIDATOR] Unknown action_type: '{original_action}' -> '{action_type}' -> 'other'")
        return 'other'
    
    print(f"✅ [VALIDATOR] Valid action_type: '{original_action}' -> '{action_type}'")
    return action_type

def create_safe_path(base_dir: str, filename: str) -> str:
    """Create a safe file path, preventing directory traversal"""
    # Sanitize the filename
    safe_filename = sanitize_filename(filename)
    
    # Create the full path
    full_path = os.path.join(base_dir, safe_filename)
    
    # Ensure the path is within the base directory
    real_base = os.path.realpath(base_dir)
    real_path = os.path.realpath(full_path)
    
    if not real_path.startswith(real_base):
        raise ValueError("Path traversal attempt detected")
    
    return full_path