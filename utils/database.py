import os
from datetime import datetime
from urllib.parse import urlparse
from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager, contextmanager
from .validators import sanitize_user_id, sanitize_text, validate_action_type, validate_audio_filename

# Try to import async SQLAlchemy components
try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    ASYNC_AVAILABLE = True
except ImportError:
    print("Warning: async SQLAlchemy not available. Falling back to sync mode.")
    ASYNC_AVAILABLE = False

Base = declarative_base()

# Database Models
class ChatLog(Base):
    __tablename__ = 'chat_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(String(255), nullable=False)
    message = Column(Text)
    reply = Column(Text)
    action_type = Column(String(100))
    gemini_call = Column(Boolean, default=False)
    gemini_output_url = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class TTSLog(Base):
    __tablename__ = 'tts_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(String(255), nullable=False)
    text = Column(Text)
    audio_filename = Column(String(255))
    audio_url = Column(Text)
    drive_link = Column(Text)
    status = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

class VoicemailLog(Base):
    __tablename__ = 'voicemail_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_id = Column(String(255), nullable=False)
    audio_filename = Column(String(255))
    transcription = Column(Text)
    translation = Column(Text)
    drive_link = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database connection setup
def get_async_db_engine():
    """Get async database engine"""
    if not ASYNC_AVAILABLE:
        raise RuntimeError("Async database support not available. Please install asyncpg.")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")
    
    # Parse the URL to extract components
    parsed = urlparse(database_url)
    
    # Construct async connection string
    async_url = f"postgresql+asyncpg://{parsed.username}:{parsed.password}@{parsed.hostname}{parsed.path}?ssl=require"
    
    engine = create_async_engine(
        async_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False  # Set to True for debugging
    )
    return engine

async def init_db():
    """Initialize database tables"""
    engine = get_async_db_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def get_async_db_session():
    """Provide an async transactional scope for database operations"""
    engine = get_async_db_engine()
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Async helper functions for logging (with sync fallback)
async def log_chat_to_db(user_id, message, reply, action_type=None, gemini_call=False, gemini_output_url=None):
    """Log chat interaction to database asynchronously with input validation"""
    if not ASYNC_AVAILABLE:
        # Fallback to sync version
        return _log_chat_to_db_sync(user_id, message, reply, action_type, gemini_call, gemini_output_url)
    
    try:
        # Validate and sanitize inputs
        user_id = sanitize_user_id(user_id)
        message = sanitize_text(message) if message else None
        reply = sanitize_text(reply, max_length=1000) if reply else None
        action_type = validate_action_type(action_type)
        gemini_output_url = sanitize_text(gemini_output_url, max_length=500) if gemini_output_url else None
        
        print(f"🔍 [DB] About to log - Action: '{action_type}', Gemini: {gemini_call}")
        
        async with get_async_db_session() as session:
            log = ChatLog(
                user_id=user_id,
                message=message,
                reply=reply,
                action_type=action_type,
                gemini_call=bool(gemini_call),
                gemini_output_url=gemini_output_url
            )
            print(f"🔍 [DB] Created ChatLog object with action_type='{log.action_type}'")
            session.add(log)
            await session.commit()
            print(f"✅ [DB] Chat log saved - User: {user_id[:8]}..., Action: {action_type or 'chat'}, Saved action: {log.action_type}")
            return True
    except ValueError as e:
        print(f"❌ [DB] Validation error: {e}")
        return False
    except Exception as e:
        print(f"❌ [DB] Failed to log chat to Neon database: {e}")
        return False

async def log_tts_to_db(user_id, text, audio_filename, audio_url, drive_link=None, status="success"):
    """Log TTS generation to database asynchronously"""
    if not ASYNC_AVAILABLE:
        # Fallback to sync version
        return _log_tts_to_db_sync(user_id, text, audio_filename, audio_url, drive_link, status)
    
    try:
        async with get_async_db_session() as session:
            log = TTSLog(
                user_id=user_id,
                text=text[:1000] if text else None,  # Limit text length
                audio_filename=audio_filename,
                audio_url=audio_url,
                drive_link=drive_link,
                status=status
            )
            session.add(log)
            await session.commit()
            print(f"✅ [DB] TTS log saved - User: {user_id[:8]}..., File: {audio_filename}")
            return True
    except Exception as e:
        print(f"❌ [DB] Failed to log TTS to Neon database: {e}")
        return False

async def log_voicemail_to_db(user_id, audio_filename, transcription, translation, drive_link=None):
    """Log voicemail to database asynchronously"""
    if not ASYNC_AVAILABLE:
        # Fallback to sync version
        return _log_voicemail_to_db_sync(user_id, audio_filename, transcription, translation, drive_link)
    
    try:
        async with get_async_db_session() as session:
            log = VoicemailLog(
                user_id=user_id,
                audio_filename=audio_filename,
                transcription=transcription,
                translation=translation,
                drive_link=drive_link
            )
            session.add(log)
            await session.commit()
            print(f"✅ [DB] Voicemail log saved - User: {user_id[:8]}..., File: {audio_filename}")
            return True
    except Exception as e:
        print(f"❌ [DB] Failed to log voicemail to Neon database: {e}")
        return False

# Sync fallback functions
def _log_chat_to_db_sync(user_id, message, reply, action_type=None, gemini_call=False, gemini_output_url=None):
    """Sync fallback for chat logging with validation"""
    try:
        # Validate and sanitize inputs
        user_id = sanitize_user_id(user_id)
        message = sanitize_text(message) if message else None
        reply = sanitize_text(reply, max_length=1000) if reply else None
        action_type = validate_action_type(action_type)
        gemini_output_url = sanitize_text(gemini_output_url, max_length=500) if gemini_output_url else None
        
        with get_db_session_sync() as session:
            log = ChatLog(
                user_id=user_id,
                message=message,
                reply=reply,
                action_type=action_type,
                gemini_call=bool(gemini_call),
                gemini_output_url=gemini_output_url
            )
            session.add(log)
            print(f"✅ [DB-SYNC] Chat log saved - User: {user_id[:8]}..., Action: {action_type or 'chat'}")
            return True
    except ValueError as e:
        print(f"❌ [DB-SYNC] Validation error: {e}")
        return False
    except Exception as e:
        print(f"❌ [DB-SYNC] Failed to log chat to Neon database: {e}")
        return False

def _log_tts_to_db_sync(user_id, text, audio_filename, audio_url, drive_link=None, status="success"):
    """Sync fallback for TTS logging"""
    try:
        with get_db_session_sync() as session:
            log = TTSLog(
                user_id=user_id,
                text=text[:1000] if text else None,
                audio_filename=audio_filename,
                audio_url=audio_url,
                drive_link=drive_link,
                status=status
            )
            session.add(log)
            print(f"✅ [DB-SYNC] TTS log saved - User: {user_id[:8]}..., File: {audio_filename}")
            return True
    except Exception as e:
        print(f"❌ [DB-SYNC] Failed to log TTS to Neon database: {e}")
        return False

def _log_voicemail_to_db_sync(user_id, audio_filename, transcription, translation, drive_link=None):
    """Sync fallback for voicemail logging"""
    try:
        with get_db_session_sync() as session:
            log = VoicemailLog(
                user_id=user_id,
                audio_filename=audio_filename,
                transcription=transcription,
                translation=translation,
                drive_link=drive_link
            )
            session.add(log)
            print(f"✅ [DB-SYNC] Voicemail log saved - User: {user_id[:8]}..., File: {audio_filename}")
            return True
    except Exception as e:
        print(f"❌ [DB-SYNC] Failed to log voicemail to Neon database: {e}")
        return False

# Backward compatibility: sync wrapper functions
def get_db_engine():
    """Legacy sync engine getter - for migration purposes only"""
    import warnings
    warnings.warn("get_db_engine is deprecated. Use get_async_db_engine instead.", DeprecationWarning)
    connection_string = os.getenv("CONNECTION_STRING")
    if not connection_string:
        # Try to use DATABASE_URL instead
        connection_string = os.getenv("DATABASE_URL")
    
    if not connection_string:
        raise ValueError("DATABASE_URL not found in environment variables")
    
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool
    
    engine = create_engine(
        connection_string,
        poolclass=NullPool,
        connect_args={
            "sslmode": "require",
            "connect_timeout": 10
        }
    )
    return engine

@contextmanager  
def get_db_session_sync():
    """Provide a transactional scope for sync database operations"""
    engine = get_db_engine()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

@asynccontextmanager
async def get_db_session():
    """Legacy sync session getter - redirects to async version"""
    import warnings
    warnings.warn("get_db_session is deprecated. Use get_async_db_session instead.", DeprecationWarning)
    async with get_async_db_session() as session:
        yield session