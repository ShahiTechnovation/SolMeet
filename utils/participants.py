"""
Participants management utilities for the SolMeet bot.
Handles tracking event participants and sending notifications.
"""

import logging
import json
import time
from typing import Dict, List, Optional, Set, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Define the participants storage directory
PARTICIPANTS_DIR = Path("./participants")

# In-memory cache of participants
events_participants = {}  # event_id -> {wallet_address -> user_info}
notifications_subscribers = {}  # event_id -> [creator_user_id, other_subscribers]

def ensure_participants_directory():
    """Ensure the participants directory exists."""
    if not PARTICIPANTS_DIR.exists():
        PARTICIPANTS_DIR.mkdir(parents=True)
        logger.info(f"Created participants directory at {PARTICIPANTS_DIR}")

def get_event_file_path(event_id: str) -> Path:
    """Get the path to the event participants file."""
    ensure_participants_directory()
    return PARTICIPANTS_DIR / f"{event_id}.json"

def save_event_participants(event_id: str):
    """Save the event participants to file."""
    try:
        file_path = get_event_file_path(event_id)
        event_data = {
            "participants": events_participants.get(event_id, {}),
            "subscribers": notifications_subscribers.get(event_id, []),
            "last_updated": int(time.time())
        }
        
        with open(file_path, 'w') as f:
            json.dump(event_data, f)
            
        logger.info(f"Saved participants data for event {event_id}")
    except Exception as e:
        logger.error(f"Error saving participants for event {event_id}: {e}")

def load_event_participants(event_id: str) -> bool:
    """
    Load the event participants from file.
    
    Returns:
        True if the file was loaded successfully, False otherwise
    """
    try:
        file_path = get_event_file_path(event_id)
        if not file_path.exists():
            logger.info(f"No participants file exists for event {event_id}")
            return False
            
        with open(file_path, 'r') as f:
            event_data = json.load(f)
            
        # Update the in-memory cache
        events_participants[event_id] = event_data.get("participants", {})
        notifications_subscribers[event_id] = event_data.get("subscribers", [])
        
        logger.info(f"Loaded participants data for event {event_id}")
        return True
    except Exception as e:
        logger.error(f"Error loading participants for event {event_id}: {e}")
        return False

def add_event_participant(
    event_id: str, 
    wallet_address: str, 
    user_id: int, 
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> bool:
    """
    Add a participant to an event and notify subscribers.
    
    Args:
        event_id: The event ID
        wallet_address: The participant's wallet address
        user_id: The participant's Telegram user ID
        username: The participant's Telegram username (optional)
        first_name: The participant's first name (optional)
        last_name: The participant's last name (optional)
        
    Returns:
        True if the participant was added successfully, False otherwise
    """
    # Load the current participants if not already in memory
    if event_id not in events_participants:
        load_event_participants(event_id)
        if event_id not in events_participants:
            events_participants[event_id] = {}
            
    # Get the user info to store
    user_info = {
        "user_id": user_id,
        "joined_at": int(time.time())
    }
    
    if username:
        user_info["username"] = username
    if first_name:
        user_info["first_name"] = first_name
    if last_name:
        user_info["last_name"] = last_name
        
    # Add the participant
    events_participants[event_id][wallet_address] = user_info
    
    # Save to disk
    save_event_participants(event_id)
    
    logger.info(f"Added participant {wallet_address} (user: {user_id}) to event {event_id}")
    return True

def remove_event_participant(event_id: str, wallet_address: str) -> bool:
    """
    Remove a participant from an event.
    
    Args:
        event_id: The event ID
        wallet_address: The participant's wallet address
        
    Returns:
        True if the participant was removed successfully, False otherwise
    """
    # Load the current participants if not already in memory
    if event_id not in events_participants:
        load_event_participants(event_id)
        if event_id not in events_participants:
            logger.info(f"No participants for event {event_id}")
            return False
            
    # Check if the participant exists
    if wallet_address not in events_participants[event_id]:
        logger.info(f"Participant {wallet_address} not found in event {event_id}")
        return False
        
    # Remove the participant
    del events_participants[event_id][wallet_address]
    
    # Save to disk
    save_event_participants(event_id)
    
    logger.info(f"Removed participant {wallet_address} from event {event_id}")
    return True

def get_event_participants(event_id: str) -> Dict[str, Dict[str, Any]]:
    """
    Get the participants of an event.
    
    Args:
        event_id: The event ID
        
    Returns:
        A dictionary of wallet addresses to user info
    """
    # Load the current participants if not already in memory
    if event_id not in events_participants:
        load_event_participants(event_id)
        if event_id not in events_participants:
            return {}
            
    return events_participants[event_id]

def count_event_participants(event_id: str) -> int:
    """
    Count the number of participants in an event.
    
    Args:
        event_id: The event ID
        
    Returns:
        The number of participants
    """
    participants = get_event_participants(event_id)
    return len(participants)

def subscribe_to_event_notifications(event_id: str, user_id: int) -> bool:
    """
    Subscribe a user to receive notifications about an event.
    
    Args:
        event_id: The event ID
        user_id: The user ID to subscribe
        
    Returns:
        True if the user was subscribed successfully, False otherwise
    """
    # Load the current subscribers if not already in memory
    if event_id not in notifications_subscribers:
        load_event_participants(event_id)
        if event_id not in notifications_subscribers:
            notifications_subscribers[event_id] = []
            
    # Add the subscriber if not already present
    if user_id not in notifications_subscribers[event_id]:
        notifications_subscribers[event_id].append(user_id)
        
        # Save to disk
        save_event_participants(event_id)
        
        logger.info(f"Subscribed user {user_id} to notifications for event {event_id}")
        return True
    else:
        logger.info(f"User {user_id} is already subscribed to notifications for event {event_id}")
        return False

def unsubscribe_from_event_notifications(event_id: str, user_id: int) -> bool:
    """
    Unsubscribe a user from receiving notifications about an event.
    
    Args:
        event_id: The event ID
        user_id: The user ID to unsubscribe
        
    Returns:
        True if the user was unsubscribed successfully, False otherwise
    """
    # Load the current subscribers if not already in memory
    if event_id not in notifications_subscribers:
        load_event_participants(event_id)
        if event_id not in notifications_subscribers:
            return False
            
    # Remove the subscriber if present
    if user_id in notifications_subscribers[event_id]:
        notifications_subscribers[event_id].remove(user_id)
        
        # Save to disk
        save_event_participants(event_id)
        
        logger.info(f"Unsubscribed user {user_id} from notifications for event {event_id}")
        return True
    else:
        logger.info(f"User {user_id} is not subscribed to notifications for event {event_id}")
        return False

def get_event_notification_subscribers(event_id: str) -> List[int]:
    """
    Get the list of user IDs subscribed to notifications for an event.
    
    Args:
        event_id: The event ID
        
    Returns:
        A list of user IDs
    """
    # Load the current subscribers if not already in memory
    if event_id not in notifications_subscribers:
        load_event_participants(event_id)
        if event_id not in notifications_subscribers:
            return []
            
    return notifications_subscribers[event_id]

def format_participant_name(participant_info: Dict[str, Any]) -> str:
    """
    Format a participant's name for display.
    
    Args:
        participant_info: The participant info dictionary
        
    Returns:
        A formatted display name
    """
    if participant_info.get("username"):
        return f"@{participant_info['username']}"
    elif participant_info.get("first_name"):
        if participant_info.get("last_name"):
            return f"{participant_info['first_name']} {participant_info['last_name']}"
        return participant_info['first_name']
    else:
        return f"User {participant_info['user_id']}"

def format_participants_list(event_id: str) -> str:
    """
    Format the list of participants for display.
    
    Args:
        event_id: The event ID
        
    Returns:
        A formatted string listing the participants
    """
    participants = get_event_participants(event_id)
    
    if not participants:
        return "No participants yet."
        
    lines = ["*Event Participants:*"]
    for i, (wallet, info) in enumerate(participants.items(), 1):
        name = format_participant_name(info)
        wallet_short = wallet[:6] + "..." + wallet[-4:]
        lines.append(f"{i}. {name} - `{wallet_short}`")
        
    return "\n".join(lines)