"""
Utility functions for the SolMeet Telegram bot.
"""

import logging
from typing import Any, Dict, Optional, Union

from telegram._message import Message
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Helper functions for Telegram message handling

async def safe_message_reply(message, text: str, **kwargs) -> None:
    """
    Safely reply to a message handling MaybeInaccessibleMessage type issues.
    
    Args:
        message: The message object, which might be MaybeInaccessibleMessage
        text: The text to reply with
        **kwargs: Additional arguments to pass to reply_text
    """
    if message and hasattr(message, 'reply_text'):
        await message.reply_text(text, **kwargs)
    else:
        logger.warning("Cannot reply to message: message is not accessible or invalid type")
        
async def safe_photo_reply(message, photo, **kwargs) -> None:
    """
    Safely reply with a photo handling MaybeInaccessibleMessage type issues.
    
    Args:
        message: The message object, which might be MaybeInaccessibleMessage
        photo: The photo to reply with
        **kwargs: Additional arguments to pass to reply_photo
    """
    if message and hasattr(message, 'reply_photo'):
        await message.reply_photo(photo, **kwargs)
    else:
        logger.warning("Cannot reply with photo: message is not accessible or invalid type")

async def safe_edit_message_text(obj, text: str, **kwargs) -> None:
    """
    Safely edit message text handling None cases.
    
    Args:
        obj: The object with edit_message_text method
        text: The new text
        **kwargs: Additional arguments to pass to edit_message_text
    """
    if obj and hasattr(obj, 'edit_message_text'):
        await obj.edit_message_text(text, **kwargs)
    else:
        logger.warning("Cannot edit message: object is None or has no edit_message_text method")

async def safe_answer(obj, text: str, **kwargs) -> None:
    """
    Safely answer to a callback query handling None cases.
    
    Args:
        obj: The object with answer method (usually callback query)
        text: The text to answer with
        **kwargs: Additional arguments to pass to answer
    """
    if obj and hasattr(obj, 'answer'):
        await obj.answer(text, **kwargs)
    else:
        logger.warning("Cannot answer callback: object is None or has no answer method")

def safe_get_chat_id(message) -> Optional[int]:
    """
    Safely get chat_id from message handling MaybeInaccessibleMessage type issues.
    
    Args:
        message: The message object, which might be MaybeInaccessibleMessage
        
    Returns:
        The chat_id or None if not available
    """
    if message and hasattr(message, 'chat_id'):
        return message.chat_id
    return None
