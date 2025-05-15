"""
Faucet handler for requesting Devnet SOL tokens.
"""

import logging
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from utils.here_wallet import get_wallet_by_user_id
from utils.solana import request_airdrop, get_sol_balance
from utils.keyboard import get_main_keyboard

logger = logging.getLogger(__name__)

# Store faucet request times to limit requests
faucet_requests = {}


async def faucet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /faucet command. Allows users to request SOL on Devnet.
    """
    user_id = update.effective_user.id
    user = update.effective_user
    user_wallet = get_wallet_by_user_id(user_id)
    
    if not user_wallet:
        await update.message.reply_text(
            "You need to connect your wallet first before requesting SOL.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect")]
            ])
        )
        return
    
    # Check if user has requested recently (limit to once per hour)
    if user_id in faucet_requests:
        last_request = faucet_requests[user_id]
        current_time = asyncio.get_event_loop().time()
        
        if current_time - last_request < 3600:  # 1 hour in seconds
            minutes_left = int((3600 - (current_time - last_request)) / 60)
            await update.message.reply_text(
                f"You've already requested SOL recently. Please wait {minutes_left} minutes before requesting again.",
                reply_markup=get_main_keyboard()
            )
            return
    
    # Get current balance
    initial_balance = await get_sol_balance(user_wallet)
    
    # Send initial message
    message = await update.message.reply_text(
        f"Requesting 1 SOL from Devnet faucet for {user.first_name}...\n"
        f"Current balance: {initial_balance} SOL"
    )
    
    try:
        # Request SOL from faucet
        tx_signature = await request_airdrop(user_wallet, 1.0)
        
        # Update the request timestamp
        faucet_requests[user_id] = asyncio.get_event_loop().time()
        
        # Wait a moment for the transaction to complete
        await asyncio.sleep(2)
        
        # Get new balance
        new_balance = await get_sol_balance(user_wallet)
        
        success_text = (
            "✅ *SOL Airdrop Successful!*\n\n"
            f"*Previous Balance:* {initial_balance} SOL\n"
            f"*New Balance:* {new_balance} SOL\n"
            f"*Amount Received:* {new_balance - initial_balance} SOL\n\n"
            f"[View Transaction on Explorer](https://explorer.solana.com/tx/{tx_signature}?cluster=devnet)"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Create Event", callback_data="event_create"),
                InlineKeyboardButton("Join Event", callback_data="event_join")
            ],
            [InlineKeyboardButton("Back to Menu", callback_data="start")]
        ])
        
        await message.edit_text(
            success_text,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Faucet error: {e}")
        await message.edit_text(
            "❌ There was an error requesting SOL from the faucet. Please try again later.",
            reply_markup=get_main_keyboard()
        )
