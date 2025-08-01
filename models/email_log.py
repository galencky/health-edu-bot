"""
Email Log Model - Structured email logging
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class EmailLog:
    """Structured email log with consistent formatting"""
    timestamp: str
    user_id: str
    recipient: str
    subject: str
    topic: str
    language: str
    content: str
    original_length: int
    translated_length: int
    references_count: int
    
    @classmethod
    def create(cls, user_id: str, to_email: str, subject: str, content: str,
              topic: str, zh: Optional[str], translated: Optional[str],
              translated_lang: Optional[str], references: list) -> 'EmailLog':
        """Factory method to create EmailLog from mail handler data"""
        return cls(
            timestamp=datetime.now().strftime('%Y%m%d_%H%M%S'),
            user_id=user_id,
            recipient=to_email,
            subject=subject,
            topic=topic,
            language=translated_lang or 'Chinese only',
            content=content,
            original_length=len(zh) if zh else 0,
            translated_length=len(translated) if translated else 0,
            references_count=len(references)
        )
    
    def to_text(self) -> str:
        """Convert to formatted text log for R2 upload"""
        return f"""Email Log
========================================
Timestamp: {self.timestamp}
User ID: {self.user_id}
Recipient: {self.recipient}
Subject: {self.subject}
Topic: {self.topic}
Language: {self.language}

Email Content:
========================================
{self.content}

Metadata:
========================================
Original content length: {self.original_length} characters
Translated content length: {self.translated_length} characters
References count: {self.references_count}
"""