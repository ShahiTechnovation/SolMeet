"""
Join request management utilities for the SolMeet bot.
Handles tracking and processing of event join requests.
"""

import json
import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# In-memory cache of event join requests
# Structure: {event_id: {wallet_address: {request_info}}}
EVENT_REQUESTS = {}

def ensure_requests_directory():
    """Ensure the join requests directory exists."""
    requests_dir = Path("join_requests")
    requests_dir.mkdir(exist_ok=True)
    return requests_dir

def get_request_file_path(event_id: str) -> Path:
    """Get the path to the join request file."""
    requests_dir = ensure_requests_directory()
    return requests_dir / f"{event_id}_requests.json"

def save_event_requests(event_id: str):
    """Save the event join requests to file."""
    if event_id not in EVENT_REQUESTS:
        logger.warning(f"No requests to save for event {event_id}")
        return False
    
    try:
        file_path = get_request_file_path(event_id)
        with open(file_path, "w") as f:
            json.dump(EVENT_REQUESTS[event_id], f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving requests for event {event_id}: {e}")
        return False

def load_event_requests(event_id: str) -> bool:
    """
    Load the event join requests from file.
    
    Returns:
        True if the file was loaded successfully, False otherwise
    """
    file_path = get_request_file_path(event_id)
    if not file_path.exists():
        # Initialize an empty dictionary for this event
        EVENT_REQUESTS[event_id] = {}
        return False
    
    try:
        with open(file_path, "r") as f:
            EVENT_REQUESTS[event_id] = json.load(f)
        return True
    except Exception as e:
        logger.error(f"Error loading requests for event {event_id}: {e}")
        EVENT_REQUESTS[event_id] = {}
        return False

def add_join_request(
    event_id: str, 
    wallet_address: str, 
    user_id: int, 
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> bool:
    """
    Add a join request for an event.
    
    Args:
        event_id: The event ID
        wallet_address: The requester's wallet address
        user_id: The requester's Telegram user ID
        username: The requester's Telegram username (optional)
        first_name: The requester's first name (optional)
        last_name: The requester's last name (optional)
        
    Returns:
        True if the request was added successfully, False otherwise
    """
    try:
        # Load existing requests
        if event_id not in EVENT_REQUESTS:
            load_event_requests(event_id)
            
        # Initialize if still not present
        if event_id not in EVENT_REQUESTS:
            EVENT_REQUESTS[event_id] = {}
            
        # Add the request
        EVENT_REQUESTS[event_id][wallet_address] = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "requested_at": time.time(),
            "status": "pending"
        }
        
        # Save to file
        return save_event_requests(event_id)
    except Exception as e:
        logger.error(f"Error adding join request: {e}")
        return False

def get_event_requests(event_id: str) -> Dict[str, Dict[str, Any]]:
    """
    Get the pending join requests for an event.
    
    Args:
        event_id: The event ID
        
    Returns:
        A dictionary of wallet addresses to request info
    """
    if event_id not in EVENT_REQUESTS:
        load_event_requests(event_id)
        
    return EVENT_REQUESTS.get(event_id, {})

def count_event_requests(event_id: str) -> int:
    """
    Count the number of pending join requests for an event.
    
    Args:
        event_id: The event ID
        
    Returns:
        The number of pending requests
    """
    requests = get_event_requests(event_id)
    return sum(1 for req in requests.values() if req.get("status") == "pending")

def approve_join_request(
    event_id: str, 
    wallet_address: str,
    approved_by_user_id: int
) -> bool:
    """
    Approve a join request for an event.
    
    Args:
        event_id: The event ID
        wallet_address: The requester's wallet address
        approved_by_user_id: User ID of the approver (must be event creator)
        
    Returns:
        True if the request was approved successfully, False otherwise
    """
    try:
        # Load requests if not already loaded
        if event_id not in EVENT_REQUESTS:
            load_event_requests(event_id)
            
        # Check if the request exists
        if event_id not in EVENT_REQUESTS or wallet_address not in EVENT_REQUESTS[event_id]:
            logger.error(f"Request not found for wallet {wallet_address} in event {event_id}")
            return False
            
        # Check if the request is pending
        if EVENT_REQUESTS[event_id][wallet_address].get("status") != "pending":
            logger.error(f"Request for wallet {wallet_address} in event {event_id} is not pending")
            return False
            
        # Update the request status
        EVENT_REQUESTS[event_id][wallet_address]["status"] = "approved"
        EVENT_REQUESTS[event_id][wallet_address]["approved_by"] = approved_by_user_id
        EVENT_REQUESTS[event_id][wallet_address]["approved_at"] = time.time()
        
        # Save to file
        return save_event_requests(event_id)
    except Exception as e:
        logger.error(f"Error approving join request: {e}")
        return False

def decline_join_request(
    event_id: str, 
    wallet_address: str,
    declined_by_user_id: int
) -> bool:
    """
    Decline a join request for an event.
    
    Args:
        event_id: The event ID
        wallet_address: The requester's wallet address
        declined_by_user_id: User ID of the decliner (must be event creator)
        
    Returns:
        True if the request was declined successfully, False otherwise
    """
    try:
        # Load requests if not already loaded
        if event_id not in EVENT_REQUESTS:
            load_event_requests(event_id)
            
        # Check if the request exists
        if event_id not in EVENT_REQUESTS or wallet_address not in EVENT_REQUESTS[event_id]:
            logger.error(f"Request not found for wallet {wallet_address} in event {event_id}")
            return False
            
        # Check if the request is pending
        if EVENT_REQUESTS[event_id][wallet_address].get("status") != "pending":
            logger.error(f"Request for wallet {wallet_address} in event {event_id} is not pending")
            return False
            
        # Update the request status
        EVENT_REQUESTS[event_id][wallet_address]["status"] = "declined"
        EVENT_REQUESTS[event_id][wallet_address]["declined_by"] = declined_by_user_id
        EVENT_REQUESTS[event_id][wallet_address]["declined_at"] = time.time()
        
        # Save to file
        return save_event_requests(event_id)
    except Exception as e:
        logger.error(f"Error declining join request: {e}")
        return False

def get_event_by_id(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the event details by ID.
    
    Args:
        event_id: The event ID
        
    Returns:
        The event data as a dictionary, or None if not found
    """
    try:
        # Check if the event exists
        events_dir = Path("events")
        event_file = events_dir / f"{event_id}.json"
        
        if not event_file.exists():
            logger.error(f"Event file not found for event {event_id}")
            return None
            
        # Load the event data
        with open(event_file, "r") as f:
            event_data = json.load(f)
            
        return event_data
    except Exception as e:
        logger.error(f"Error loading event data: {e}")
        return None


def get_event_organizer_id(event_id: str) -> Optional[int]:
    """
    Get the user ID of the event organizer.
    
    Args:
        event_id: The event ID
        
    Returns:
        The user ID of the event organizer, or None if not found
    """
    try:
        # Get the event data
        event_data = get_event_by_id(event_id)
        if not event_data:
            return None
            
        # Get the organizer ID
        organizer_id = event_data.get("creator_id")
        if organizer_id:
            return int(organizer_id)
            
        return None
    except Exception as e:
        logger.error(f"Error getting event organizer: {e}")
        return None

def get_request_status(event_id: str, wallet_address: str) -> str:
    """
    Get the status of a join request.
    
    Args:
        event_id: The event ID
        wallet_address: The requester's wallet address
        
    Returns:
        The status of the request ("pending", "approved", "declined", or "none")
    """
    try:
        # Load requests if not already loaded
        if event_id not in EVENT_REQUESTS:
            load_event_requests(event_id)
            
        # Check if the request exists
        if event_id not in EVENT_REQUESTS or wallet_address not in EVENT_REQUESTS[event_id]:
            return "none"
            
        # Return the status
        return EVENT_REQUESTS[event_id][wallet_address].get("status", "none")
    except Exception as e:
        logger.error(f"Error getting request status: {e}")
        return "none"

def format_request_name(request_info: Dict[str, Any]) -> str:
    """
    Format a requester's name for display.
    
    Args:
        request_info: The request info dictionary
        
    Returns:
        A formatted display name
    """
    if not request_info:
        return "Unknown User"
        
    # Try to format the name
    if request_info.get("username"):
        return f"@{request_info['username']}"
    elif request_info.get("first_name"):
        if request_info.get("last_name"):
            return f"{request_info['first_name']} {request_info['last_name']}"
        return request_info["first_name"]
    else:
        return f"User {request_info.get('user_id', 'Unknown')}"

def format_requests_list(event_id: str) -> str:
    """
    Format the list of pending requests for display.
    
    Args:
        event_id: The event ID
        
    Returns:
        A formatted string listing the pending requests
    """
    requests = get_event_requests(event_id)
    
    # Filter for pending requests
    pending_requests = {k: v for k, v in requests.items() if v.get("status") == "pending"}
    
    if not pending_requests:
        return "No pending join requests for this event."
        
    # Format the list
    result = []
    for wallet, request_info in pending_requests.items():
        name = format_request_name(request_info)
        wallet_short = f"{wallet[:6]}...{wallet[-4:]}"
        result.append(f"• {name} ({wallet_short})")
        
    return "\n".join(result)