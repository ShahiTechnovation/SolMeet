#!/usr/bin/env python3
"""
Test script for checking Solana RPC interactions.
"""

import asyncio
import logging

from utils.solana import get_sol_balance, request_airdrop
from utils.wallet_creator import list_user_wallets

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def test_solana_interactions():
    """Test Solana blockchain interactions."""
    # Get available wallets
    wallets = list_user_wallets()
    if not wallets:
        logger.error("No wallets found! Please run test_wallet_creation.py first.")
        return
        
    # Pick the first wallet
    test_wallet = next(iter(wallets.keys()))
    logger.info(f"Testing with wallet: {test_wallet}")
    
    # Check balance
    try:
        balance = await get_sol_balance(test_wallet)
        logger.info(f"✅ Current balance: {balance} SOL")
    except Exception as e:
        logger.error(f"❌ Error getting balance: {e}")
    
    # Request an airdrop
    try:
        tx_sig = await request_airdrop(test_wallet, 1.0)
        logger.info(f"✅ Airdrop requested: {tx_sig}")
        
        # Check balance again after airdrop
        await asyncio.sleep(2)  # Brief pause to allow transaction to process
        new_balance = await get_sol_balance(test_wallet)
        logger.info(f"✅ Updated balance: {new_balance} SOL")
    except Exception as e:
        logger.error(f"❌ Error requesting airdrop: {e}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_solana_interactions())