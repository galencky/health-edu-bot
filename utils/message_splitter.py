"""
LINE message splitting utilities
Handles splitting long messages into multiple bubbles while respecting LINE's limits
"""
from typing import List, Tuple
import re

# LINE API Limits
MAX_BUBBLE_COUNT = 5  # Maximum bubbles in one reply message (LINE hard limit)
MAX_CONTENT_BUBBLES = 3  # Max content bubbles (leaving room for references and main reply)
MAX_TEXT_LENGTH = 5000  # LINE's maximum text message length (API limit)
MAX_CHARS_PER_BUBBLE = 1000  # Maximum characters per bubble for readability
SAFE_CHARS_PER_BUBBLE = 950  # Safe limit with some buffer

def split_long_text(text: str, prefix: str = "", max_bubbles: int = MAX_CONTENT_BUBBLES) -> List[str]:
    """
    Split long text into multiple chunks for LINE bubbles
    
    Args:
        text: The text to split
        prefix: Prefix to add to each chunk (e.g., "📄 原文：\n")
        max_bubbles: Maximum number of bubbles to create
        
    Returns:
        List of text chunks, each suitable for a LINE bubble
    """
    if not text:
        return []
    
    # Calculate available length per bubble (accounting for prefix)
    prefix_length = len(prefix)
    available_length = SAFE_CHARS_PER_BUBBLE - prefix_length - 10  # Extra buffer for safety
    
    # If text fits in one bubble, return as is
    if len(text) <= available_length:
        return [prefix + text]
    
    chunks = []
    remaining_text = text
    
    for i in range(max_bubbles):
        if not remaining_text:
            break
            
        # For the last bubble, we might need to truncate
        if i == max_bubbles - 1:
            # Check if remaining text fits
            if len(remaining_text) > available_length:
                # Truncate with ellipsis
                chunk = remaining_text[:available_length - 5] + "\n..."
            else:
                chunk = remaining_text
            chunks.append(prefix + chunk)
            break
        
        # Try to find a good break point
        chunk_text = remaining_text[:available_length]
        
        # Look for natural break points (in order of preference)
        break_points = [
            # Paragraph break
            chunk_text.rfind('\n\n'),
            # Sentence end
            max(chunk_text.rfind('。'), chunk_text.rfind('.')),
            # Line break
            chunk_text.rfind('\n'),
            # Comma
            max(chunk_text.rfind('，'), chunk_text.rfind(',')),
            # Any space
            chunk_text.rfind(' '),
        ]
        
        # Find the best break point
        break_point = -1
        for bp in break_points:
            if bp > available_length * 0.5:  # At least 50% of available length
                break_point = bp
                break
        
        # If no good break point, just break at the limit
        if break_point == -1:
            break_point = available_length
        
        # Create chunk
        chunk = remaining_text[:break_point].rstrip()
        remaining_text = remaining_text[break_point:].lstrip()
        
        # Add continuation indicator if not the last chunk
        if remaining_text and i < max_bubbles - 1:
            chunk += "\n(續...)"
        
        chunks.append(prefix + chunk)
    
    return chunks

def truncate_for_line(text: str, max_length: int = MAX_CHARS_PER_BUBBLE) -> str:
    """
    Truncate text to fit LINE's bubble character limit
    
    Args:
        text: Text to truncate
        max_length: Maximum allowed length (default 1000 chars)
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    
    # Truncate with ellipsis
    return text[:max_length - 5] + "\n..."

def calculate_bubble_budget(has_references: bool, has_audio: bool, has_taigi_credit: bool) -> int:
    """
    Calculate how many content bubbles we can use
    
    Args:
        has_references: Whether references bubble will be added
        has_audio: Whether audio bubble will be added
        has_taigi_credit: Whether Taigi credit bubble will be added
        
    Returns:
        Number of content bubbles available
    """
    used_bubbles = 1  # Main reply always needed
    
    if has_references:
        used_bubbles += 1
    if has_audio:
        used_bubbles += 1
    if has_taigi_credit:
        used_bubbles += 1
    
    # Calculate remaining budget for content
    content_bubbles = MAX_BUBBLE_COUNT - used_bubbles
    
    # Ensure at least 1 content bubble, max 3
    return max(1, min(content_bubbles, MAX_CONTENT_BUBBLES))