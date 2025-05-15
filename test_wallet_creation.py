#!/usr/bin/env python3
"""
Test script for creating a Solana wallet using our wallet_creator utility.
"""

import asyncio
import logging

from utils.wallet_creator import create_new_wallet, get_wallet_info, list_user_wallets
from utils.here_wallet import create_wallet_for_user, get_wallet_by_user_id

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def test_create_wallet():
    """Test creating a new wallet directly."""
    logger.info("Testing direct wallet creation...")
    
    # Test create_new_wallet function
    wallet_address, wallet_info = create_new_wallet()
    
    if not wallet_address or not wallet_info:
        logger.error("❌ Failed to create wallet!")
        return
    
    # Log wallet information
    logger.info(f"✅ Successfully created wallet!")
    logger.info(f"Wallet Address: {wallet_address}")
    logger.info(f"Mnemonic: {wallet_info.get('mnemonic', 'Not available')}")
    
    # Test get_wallet_info function
    retrieved_info = get_wallet_info(wallet_address)
    if retrieved_info:
        logger.info("✅ Successfully retrieved wallet info!")
    else:
        logger.error("❌ Failed to retrieve wallet info!")
    
    # Test list_user_wallets function
    wallets = list_user_wallets()
    logger.info(f"Available wallets: {len(wallets)}")
    for addr, label in wallets.items():
        logger.info(f"  - {label}: {addr}")
    
    # Test the user-wallet interaction
    test_user_id = 12345
    success, user_wallet_address, _ = create_wallet_for_user(test_user_id)
    
    if success:
        logger.info(f"✅ Created wallet for user {test_user_id}: {user_wallet_address}")
        
        # Verify the user-wallet linkage
        linked_address = get_wallet_by_user_id(test_user_id)
        if linked_address and linked_address == user_wallet_address:
            logger.info(f"✅ Successfully linked wallet to user!")
        else:
            logger.error(f"❌ Failed to verify wallet linkage!")
    else:
        logger.error(f"❌ Failed to create wallet for user {test_user_id}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_create_wallet())