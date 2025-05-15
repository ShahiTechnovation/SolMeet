"""
Wallet management utilities for the SolMeet bot.
Handles wallet connection, linking, and transaction signing.
"""

import os
import logging
import random
import string
from typing import Dict, Optional, Any, Tuple

from utils.wallet_creator import create_new_wallet, get_wallet_info, list_user_wallets

logger = logging.getLogger(__name__)

# Store connected wallets (in a real app, this would be a database)
connected_wallets = {}

# DApp ID for Here Wallet integration
DAPP_ID = os.getenv("HERE_WALLET_DAPP_ID", "solmeet_telegram_bot")


def generate_connect_url(user_id: int) -> str:
    """
    Generate a URL for connecting or creating a wallet.
    
    For this implementation, we'll just return a callback URL
    that the bot can handle to create a wallet.
    """
    # Generate a random state for security
    state = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    # In a real implementation with Here Wallet, this would be a real URL
    # Since we're handling wallet creation internally, we'll use a dummy URL
    connect_url = f"https://t.me/SolMeetBot?start=create_wallet_{state}"
    
    return connect_url


def get_wallet_by_user_id(user_id: int) -> Optional[str]:
    """Get a wallet address for a user ID."""
    return connected_wallets.get(user_id)


def get_user_wallets() -> Dict[str, str]:
    """
    Get all available wallets that can be linked to users.
    Returns a dictionary of wallet addresses to readable names.
    
    This is a security-sensitive function that should only return wallets
    that aren't already linked to other users.
    """
    # Get all wallets from files
    all_wallets = list_user_wallets()
    
    # Get list of wallets that are already linked to users
    linked_wallets = set(connected_wallets.values())
    
    # Filter to only show unlinked wallets
    available_wallets = {}
    for address, name in all_wallets.items():
        if address not in linked_wallets:
            available_wallets[address] = name
            
    return available_wallets


def create_wallet_for_user(user_id: int) -> Tuple[bool, Optional[str], Optional[Dict]]:
    """
    Create a new wallet and link it to the user.
    
    Returns:
        Tuple of (success, wallet_address, wallet_info)
    """
    try:
        # Create a new wallet
        wallet_address, wallet_info = create_new_wallet()
        
        if not wallet_address or not wallet_info:
            logger.error("Failed to create wallet")
            return False, None, None
            
        # Link the wallet to the user
        connected_wallets[user_id] = wallet_address
        logger.info(f"Created and linked wallet {wallet_address} to user {user_id}")
        
        return True, wallet_address, wallet_info
    except Exception as e:
        logger.error(f"Error creating wallet for user: {e}")
        return False, None, None


def link_wallet_to_user(user_id: int, wallet_address: str) -> bool:
    """
    Link a wallet address to a user ID.
    """
    try:
        # First check if the wallet exists
        wallet_info = get_wallet_info(wallet_address)
        if not wallet_info:
            logger.error(f"Cannot link non-existent wallet {wallet_address}")
            return False
            
        connected_wallets[user_id] = wallet_address
        logger.info(f"Linked wallet {wallet_address} to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error linking wallet: {e}")
        return False


async def request_transaction_signing(
    wallet_address: str,
    transaction_data: Dict[str, Any]
) -> Optional[str]:
    """
    Sign a transaction using the local wallet.
    
    In a real implementation, this would properly sign the transaction.
    For this demo, we'll simulate the signing process.
    """
    try:
        # Check if we have the wallet
        wallet_info = get_wallet_info(wallet_address)
        if not wallet_info:
            logger.error(f"Wallet not found for signing: {wallet_address}")
            return None
            
        # In a real implementation, we would use the keypair to sign the transaction
        # For now, we'll simulate a successful signing
        tx_signature = f"sig_{wallet_address[:8]}_{random.randint(1000, 9999)}"
        
        logger.info(f"Signed transaction for wallet {wallet_address}: {tx_signature}")
        return tx_signature
    except Exception as e:
        logger.error(f"Error signing transaction: {e}")
        return None
