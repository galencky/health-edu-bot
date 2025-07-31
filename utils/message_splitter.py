"""
LINE message splitting utilities
Handles splitting long messages into multiple bubbles while respecting LINE's limits
"""
from typing import List, Tuple
import re

# LINE API Limits
MAX_BUBBLE_COUNT = 5  # Maximum bubbles in one reply message (LINE hard limit)
MAX_CONTENT_BUBBLES = 3  # Max content bubbles (leaving room for references and main reply)
MAX_TOTAL_CHARS = 5000  # Maximum total characters across all bubbles
MAX_CHARS_PER_BUBBLE = 2000  # Maximum characters per bubble
SAFE_CHARS_PER_BUBBLE = 1950  # Safe limit with some buffer

def split_long_text(text: str, prefix: str = "", max_bubbles: int = MAX_CONTENT_BUBBLES, char_budget: int = None) -> List[str]:
    """
    Split long text into multiple chunks for LINE bubbles
    
    Args:
        text: The text to split
        prefix: Prefix to add to each chunk (e.g., "📄 原文：\n")
        max_bubbles: Maximum number of bubbles to create
        char_budget: Optional character budget for all content bubbles
        
    Returns:
        List of text chunks, each suitable for a LINE bubble
    """
    if not text:
        return []
    
    # Calculate available length per bubble (accounting for prefix)
    prefix_length = len(prefix)
    available_length = SAFE_CHARS_PER_BUBBLE - prefix_length
    
    # Use provided budget or default to max total chars
    if char_budget:
        total_available = char_budget - (prefix_length * max_bubbles)
    else:
        total_available = MAX_TOTAL_CHARS - (prefix_length * max_bubbles)
        
    if len(text) > total_available:
        # Text exceeds limit, will need to truncate
        text = text[:total_available]
        truncated = True
    else:
        truncated = False
    
    # If text fits in one bubble, return as is
    if len(text) <= available_length:
        if truncated:
            return [prefix + text + "\n\n⚠️ 內容因超過 LINE 限制已截斷"]
        return [prefix + text]
    
    chunks = []
    remaining_text = text
    
    for i in range(max_bubbles):
        if not remaining_text:
            break
            
        # For the last bubble
        if i == max_bubbles - 1:
            # Take whatever remains
            chunk = remaining_text
            if truncated:
                chunk += "\n\n⚠️ 內容因超過 LINE 限制已截斷"
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
        
        chunks.append(prefix + chunk)
    
    # If we still have remaining text after max bubbles, add truncation notice
    if remaining_text and not truncated:
        # Text was split across max bubbles but more remains
        if chunks:
            chunks[-1] += "\n\n⚠️ 內容因超過 LINE 限制已截斷"
    
    return chunks

def truncate_for_line(text: str, max_length: int = MAX_CHARS_PER_BUBBLE) -> str:
    """
    Truncate text to fit LINE's bubble character limit
    
    Args:
        text: Text to truncate
        max_length: Maximum allowed length (default 2000 chars)
        
    Returns:
        Truncated text with notice if needed
    """
    if len(text) <= max_length:
        return text
    
    # Truncate with notice
    truncation_notice = "\n\n⚠️ 內容因超過 LINE 限制已截斷"
    return text[:max_length - len(truncation_notice)] + truncation_notice

def calculate_total_characters(bubbles: List) -> int:
    """
    Calculate total character count across all bubbles
    
    Args:
        bubbles: List of message bubbles (TextSendMessage, FlexSendMessage, etc.)
        
    Returns:
        Total character count
    """
    total_chars = 0
    
    for bubble in bubbles:
        if hasattr(bubble, 'text'):
            # TextSendMessage
            total_chars += len(bubble.text)
        elif hasattr(bubble, 'alt_text'):
            # FlexSendMessage - count alt_text as minimum
            # Flex messages can be large, so we estimate conservatively
            total_chars += len(bubble.alt_text) * 10  # Rough estimate for flex content
        # AudioSendMessage doesn't count towards character limit
    
    return total_chars


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