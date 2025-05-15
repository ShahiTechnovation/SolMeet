"""
Join request management utilities for the SolMeet bot.
Handles tracking and processing of event join requests.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from utils.here_wallet import get_wallet_by_user_id
from utils.participants import add_event_participant, get_event_participants
from utils.solana import join_event_onchain

logger = logging.getLogger(__name__)

# Global dictionary to store pending requests by event_id -> [wallet_addresses]
_pending_requests = {}

def ensure_requests_directory():
    """Ensure the join requests directory exists."""
    requests_path = Path("events/requests")
    requests_path.mkdir(parents=True, exist_ok=True)
    return requests_path


def get_request_file_path(event_id: str) -> Path:
    """Get the path to the join request file."""
    ensure_requests_directory()
    return Path(f"events/requests/{event_id}_requests.json")


def save_event_requests(event_id: str):
    """Save the event join requests to file."""
    global _pending_requests
    
    if event_id not in _pending_requests:
        _pending_requests[event_id] = {}
        
    file_path = get_request_file_path(event_id)
    with open(file_path, "w") as f:
        json.dump(_pending_requests[event_id], f, indent=2)
    
    logger.info(f"Saved join requests data for event {event_id}")


def load_event_requests(event_id: str) -> bool:
    """
    Load the event join requests from file.
    
    Returns:
        True if the file was loaded successfully, False otherwise
    """
    global _pending_requests
    
    file_path = get_request_file_path(event_id)
    if not file_path.exists():
        logger.info(f"No join requests file exists for event {event_id}")
        _pending_requests[event_id] = {}
        return False
    
    try:
        with open(file_path, "r") as f:
            _pending_requests[event_id] = json.load(f)
        logger.info(f"Loaded join requests data for event {event_id}")
        return True
    except json.JSONDecodeError:
        logger.error(f"Error parsing join requests file for event {event_id}")
        _pending_requests[event_id] = {}
        return False
    except Exception as e:
        logger.error(f"Error loading join requests data for event {event_id}: {e}")
        _pending_requests[event_id] = {}
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
    global _pending_requests
    
    # Load requests if not already loaded
    if event_id not in _pending_requests:
        load_event_requests(event_id)
    
    # Check if already in requests
    if wallet_address in _pending_requests[event_id]:
        logger.info(f"Wallet {wallet_address} already has a pending request for event {event_id}")
        return False
    
    # Check if already a participant
    current_participants = get_event_participants(event_id)
    if wallet_address in current_participants:
        logger.info(f"Wallet {wallet_address} is already a participant of event {event_id}")
        return False
        
    # Add to pending requests
    _pending_requests[event_id][wallet_address] = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "status": "pending"
    }
    
    # Save to file
    save_event_requests(event_id)
    logger.info(f"Added join request from {wallet_address} (user: {user_id}) to event {event_id}")
    
    return True


def get_event_requests(event_id: str) -> Dict[str, Dict[str, Any]]:
    """
    Get the pending join requests for an event.
    
    Args:
        event_id: The event ID
        
    Returns:
        A dictionary of wallet addresses to request info
    """
    global _pending_requests
    
    # Load requests if not already loaded
    if event_id not in _pending_requests:
        load_event_requests(event_id)
    
    return _pending_requests[event_id]


def count_event_requests(event_id: str) -> int:
    """
    Count the number of pending join requests for an event.
    
    Args:
        event_id: The event ID
        
    Returns:
        The number of pending requests
    """
    requests = get_event_requests(event_id)
    return len(requests)


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
    global _pending_requests
    
    # Load requests if not already loaded
    if event_id not in _pending_requests:
        load_event_requests(event_id)
    
    # Check if request exists
    if wallet_address not in _pending_requests[event_id]:
        logger.warning(f"No pending request from {wallet_address} for event {event_id}")
        return False
    
    request_info = _pending_requests[event_id][wallet_address]
    
    # Add to participants
    success = add_event_participant(
        event_id=event_id,
        wallet_address=wallet_address,
        user_id=request_info["user_id"],
        username=request_info.get("username"),
        first_name=request_info.get("first_name"),
        last_name=request_info.get("last_name")
    )
    
    if success:
        # Join on-chain asynchronously
        # This can be improved to await the actual blockchain confirmation
        join_event_onchain(wallet_address, event_id)
        
        # Remove from pending requests
        del _pending_requests[event_id][wallet_address]
        save_event_requests(event_id)
        
        logger.info(f"Approved join request from {wallet_address} for event {event_id}")
        return True
    else:
        logger.error(f"Failed to add participant {wallet_address} to event {event_id}")
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
    global _pending_requests
    
    # Load requests if not already loaded
    if event_id not in _pending_requests:
        load_event_requests(event_id)
    
    # Check if request exists
    if wallet_address not in _pending_requests[event_id]:
        logger.warning(f"No pending request from {wallet_address} for event {event_id}")
        return False
    
    # Remove from pending requests
    del _pending_requests[event_id][wallet_address]
    save_event_requests(event_id)
    
    logger.info(f"Declined join request from {wallet_address} for event {event_id}")
    return True


def get_event_organizer_id(event_id: str) -> Optional[int]:
    """
    Get the user ID of the event organizer.
    
    Args:
        event_id: The event ID
        
    Returns:
        The user ID of the event organizer, or None if not found
    """
    # In a real implementation, this would query the blockchain
    # For now, we'll assume the creator is the first participant
    
    participants = get_event_participants(event_id)
    if not participants:
        return None
        
    # The first participant should be the creator
    first_wallet = next(iter(participants))
    first_participant = participants[first_wallet]
    
    return first_participant.get("user_id")


def get_request_status(event_id: str, wallet_address: str) -> str:
    """
    Get the status of a join request.
    
    Args:
        event_id: The event ID
        wallet_address: The requester's wallet address
        
    Returns:
        The status of the request ("pending", "approved", "declined", or "none")
    """
    global _pending_requests
    
    # Check if already a participant
    current_participants = get_event_participants(event_id)
    if wallet_address in current_participants:
        return "approved"
    
    # Check if pending
    if event_id not in _pending_requests:
        load_event_requests(event_id)
        
    if wallet_address in _pending_requests[event_id]:
        return _pending_requests[event_id][wallet_address].get("status", "pending")
    
    return "none"


def format_request_name(request_info: Dict[str, Any]) -> str:
    """
    Format a requester's name for display.
    
    Args:
        request_info: The request info dictionary
        
    Returns:
        A formatted display name
    """
    if request_info.get("username"):
        return f"@{request_info['username']}"
    elif request_info.get("first_name"):
        if request_info.get("last_name"):
            return f"{request_info['first_name']} {request_info['last_name']}"
        return request_info['first_name']
    else:
        return f"User {request_info['user_id']}"


def format_requests_list(event_id: str) -> str:
    """
    Format the list of pending requests for display.
    
    Args:
        event_id: The event ID
        
    Returns:
        A formatted string listing the pending requests
    """
    requests = get_event_requests(event_id)
    if not requests:
        return "No pending join requests for this event."
    
    request_lines = []
    for wallet, info in requests.items():
        name = format_request_name(info)
        request_lines.append(f"• {name} ({wallet[:6]}...{wallet[-4:]})")
    
    return "Pending Join Requests:\n" + "\n".join(request_lines)