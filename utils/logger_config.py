"""
Centralized logging configuration for MedEdBot.
Provides consistent logging format and levels across all modules.
"""

import os
import sys
from typing import Optional

# Log levels
class LogLevel:
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"
    DEBUG = "DEBUG"

# Standard log prefixes (without brackets)
class LogPrefix:
    # Core services
    API = "API"
    WEBHOOK = "WEBHOOK"
    LINE = "LINE"
    EMAIL = "EMAIL"
    
    # AI services
    GEMINI = "GEMINI"
    TAIGI = "TAIGI"
    TTS = "TTS"
    
    # Storage (preserve as-is)
    DB = "DB"  # Neon database
    R2 = "R2"  # Cloudflare R2
    
    # System
    LOGGING = "LOG"
    CLEANUP = "CLEANUP"
    STORAGE = "STORAGE"
    RETRY = "RETRY"
    MEMORY = "MEMORY"
    
    # Operations
    UPLOAD = "UPLOAD"
    AUDIO = "AUDIO"
    MODIFY = "MODIFY"

def log(level: str, prefix: str, message: str, error: Optional[Exception] = None):
    """
    Unified logging function.
    
    Args:
        level: LogLevel constant
        prefix: LogPrefix constant or custom prefix
        message: Log message
        error: Optional exception object
    """
    # Format: [PREFIX] message
    log_msg = f"[{prefix}] {message}"
    
    # Add error details if provided
    if error:
        log_msg += f" - {type(error).__name__}: {error}"
    
    # For now, just print. Can be extended to use proper logging framework
    print(log_msg)

def debug(prefix: str, message: str):
    """Log debug message"""
    if os.getenv("DEBUG", "").lower() == "true":
        log(LogLevel.DEBUG, prefix, message)

def info(prefix: str, message: str):
    """Log info message"""
    log(LogLevel.INFO, prefix, message)

def warn(prefix: str, message: str):
    """Log warning message"""
    log(LogLevel.WARN, prefix, message)

def error(prefix: str, message: str, exc: Optional[Exception] = None):
    """Log error message"""
    log(LogLevel.ERROR, prefix, message, exc)