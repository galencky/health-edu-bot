"""Authentication utilities for API endpoints"""
import os
import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from typing import Optional

# API key header name
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Get API key from environment or generate a secure one
CHAT_API_KEY = os.getenv("CHAT_API_KEY")
if not CHAT_API_KEY:
    # Generate a secure API key if not provided
    CHAT_API_KEY = secrets.token_urlsafe(32)
    print(f"⚠️  No CHAT_API_KEY found in .env")
    print(f"📝 Generated temporary API key: {CHAT_API_KEY}")
    print("   Add this to your .env file: CHAT_API_KEY=<your-secure-key>")

async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """Verify API key for protected endpoints"""
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(api_key, CHAT_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return api_key

# Optional: Function to verify LINE webhook signature
def verify_line_signature(body: bytes, signature: str) -> bool:
    """Verify LINE webhook signature"""
    import hmac
    import hashlib
    import base64
    
    channel_secret = os.getenv("LINE_CHANNEL_SECRET", "").encode('utf-8')
    if not channel_secret:
        return False
    
    hash = hmac.new(channel_secret, body, hashlib.sha256).digest()
    signature_compare = base64.b64encode(hash).decode('utf-8')
    
    # Constant-time comparison
    return secrets.compare_digest(signature, signature_compare)