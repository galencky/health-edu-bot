"""
Pydantic v2 models for session management.
Gradual migration from dict to typed models.
"""
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class SessionReferences(BaseModel):
    """References from Gemini API"""
    title: str
    url: str


class SessionBase(BaseModel):
    """Base session state - common fields"""
    # Persistent flags
    started: bool = False
    mode: Optional[Literal["edu", "chat"]] = None
    
    # Previous mode memory
    _prev_mode: Optional[Literal["edu", "chat"]] = Field(None, alias="_prev_mode")
    
    class Config:
        # Allow population by field name or alias
        populate_by_name = True


class EducationSession(BaseModel):
    """Education mode specific fields"""
    zh_output: Optional[str] = None
    translated_output: Optional[str] = None
    translated: bool = False
    awaiting_translate_language: bool = False
    awaiting_email: bool = False
    awaiting_modify: bool = False
    last_topic: Optional[str] = None
    last_translation_lang: Optional[str] = None
    references: Optional[List[dict]] = None  # Will migrate to SessionReferences later


class MedChatSession(BaseModel):
    """MedChat mode specific fields"""
    awaiting_chat_language: bool = False
    chat_target_lang: Optional[str] = None


class STTSession(BaseModel):
    """Speech-to-text specific fields"""
    awaiting_stt_translation: bool = False
    stt_transcription: Optional[str] = None
    stt_last_translation: Optional[str] = None


class TTSSession(BaseModel):
    """Text-to-speech specific fields"""
    tts_audio_url: Optional[str] = None
    tts_audio_dur: int = 0
    tts_queue: List[str] = Field(default_factory=list)


class UserSession(SessionBase, EducationSession, MedChatSession, STTSession, TTSSession):
    """
    Complete user session model combining all aspects.
    Uses Pydantic v2 multiple inheritance pattern.
    """
    # Metadata (not stored in dict, but useful for tracking)
    user_id: Optional[str] = Field(None, exclude=True)
    created_at: datetime = Field(default_factory=datetime.now, exclude=True)
    last_accessed: datetime = Field(default_factory=datetime.now, exclude=True)
    
    def to_legacy_dict(self) -> dict:
        """Convert to legacy dict format for backward compatibility"""
        return self.model_dump(exclude={'user_id', 'created_at', 'last_accessed'})
    
    @classmethod
    def from_legacy_dict(cls, data: dict) -> "UserSession":
        """Create from legacy dict format"""
        return cls(**data)
    
    def is_awaiting_input(self) -> bool:
        """Check if session is waiting for any user input"""
        return any([
            self.awaiting_translate_language,
            self.awaiting_email,
            self.awaiting_modify,
            self.awaiting_chat_language,
            self.awaiting_stt_translation
        ])
    
    def clear_awaiting_flags(self):
        """Clear all awaiting flags"""
        self.awaiting_translate_language = False
        self.awaiting_email = False
        self.awaiting_modify = False
        self.awaiting_chat_language = False
        self.awaiting_stt_translation = False


# Example migration wrapper for gradual adoption
class SessionProxy:
    """
    Proxy that can work with both dict and Pydantic model.
    Allows gradual migration without breaking existing code.
    """
    def __init__(self, data: dict):
        self._dict = data
        self._model = UserSession.from_legacy_dict(data)
    
    def __getitem__(self, key):
        # Support dict-style access
        return self._dict[key]
    
    def __setitem__(self, key, value):
        # Update both dict and model
        self._dict[key] = value
        setattr(self._model, key, value)
    
    def get(self, key, default=None):
        return self._dict.get(key, default)
    
    @property
    def model(self) -> UserSession:
        """Get the Pydantic model"""
        return self._model
    
    def sync_to_dict(self):
        """Sync model changes back to dict"""
        self._dict.update(self._model.to_legacy_dict())