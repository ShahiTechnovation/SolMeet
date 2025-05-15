"""
Start command handlers for the SolMeet bot.
"""

import logging
from typing import Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from utils.keyboard import get_main_keyboard
from utils.here_wallet import get_wallet_by_user_id

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /start command. Introduces the bot and provides initial guidance.
    """
    if not update.message:
        logger.error("No message in update for start_command")
        return
        
    user = update.effective_user
    if not user:
        logger.error("No user found in update for start_command")
        return
    
    # Simple welcome text without complex formatting or entities
    welcome_text = (
        f"Hello, {user.first_name}! Welcome to SolMeet - your Web3 Event Manager on Solana.\n\n"
        "I can help you create and join on-chain events using your Solana wallet.\n\n"
        "What can you do with SolMeet?\n"
        "- Create events with name, venue, description, and attendee limits\n"
        "- Join events with unique codes or links and claim your attendance NFT\n"
        "- Connect securely with Here Wallet - no private keys stored\n"
        "- Track your created and joined events on-chain\n\n"
        "Getting Started:\n"
        "1. First, connect your wallet with /connect\n"
        "2. Create an event with /send_create or join one with /send_join\n"
        "3. View your events with /my_events\n\n"
        "Need SOL tokens for testing? Use /faucet to get some on Devnet."
    )

    # Basic keyboard with essential options
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect"),
            InlineKeyboardButton("About SolMeet", callback_data="about")
        ],
        [
            InlineKeyboardButton("Create Event", callback_data="event_create"),
            InlineKeyboardButton("Join Event", callback_data="event_join")
        ]
    ])

    try:
        await update.message.reply_text(
            text=welcome_text,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        # Extra-simple fallback with minimal text
        try:
            await update.message.reply_text(
                "Welcome to SolMeet! Use the buttons below to navigate.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect")],
                    [InlineKeyboardButton("Menu", callback_data="start")]
                ])
            )
        except Exception as e2:
            logger.error(f"Fatal error in start command fallback: {e2}")


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for showing information about the SolMeet bot.
    """
    about_text = (
        "SolMeet | Web3 Event Bot\n\n"
        "SolMeet is a Telegram bot for creating and joining events on the Solana blockchain.\n\n"
        "Key Features:\n"
        "- Create on-chain events with custom parameters\n"
        "- Join events with unique codes and claim NFT attestations\n"
        "- Secure wallet integration via Here Wallet\n"
        "- One-claim-per-user verification\n"
        "- Track all your events in one place\n"
        "- Quick access to transaction details via Solana Explorer\n\n"
        "Technical Stack:\n"
        "- Runs on Solana Devnet\n"
        "- Anchor smart contract for on-chain operations\n"
        "- Secure transaction signing through Here Wallet\n"
        "- No private keys are ever stored by the bot\n\n"
        "Perfect for hackathons, meetups, conferences, and community events!"
    )

    try:
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(
                text=about_text,
                reply_markup=get_main_keyboard()
            )
        elif update.message:
            await update.message.reply_text(
                text=about_text,
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        logger.error(f"Error in about command: {e}")
        # Simple fallback message
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    text="SolMeet is a Web3 Event Manager on Solana. Use the buttons below to navigate.",
                    reply_markup=get_main_keyboard()
                )
            except Exception:
                pass
        elif update.message:
            try:
                await update.message.reply_text(
                    text="SolMeet is a Web3 Event Manager on Solana. Use the buttons below to navigate.",
                    reply_markup=get_main_keyboard()
                )
            except Exception:
                pass


async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for 'start' callback query (back to menu button).
    """
    if not update.callback_query:
        logger.error("No callback query in update for start_callback")
        return
        
    query = update.callback_query
    
    try:
        await query.answer()
        
        user = query.from_user
        if not user:
            logger.error("No user in callback query for start_callback")
            return
            
        user_id = user.id
        user_wallet = get_wallet_by_user_id(user_id)
        
        # Simple welcome text without complex formatting
        welcome_text = (
            f"Hello, {user.first_name}! Welcome to SolMeet - your Web3 Event Manager on Solana.\n\n"
            "What would you like to do today?"
        )

        # Different keyboard based on whether the user has a wallet
        if user_wallet:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("View Wallet", callback_data="wallet_info"),
                    InlineKeyboardButton("About SolMeet", callback_data="about")
                ],
                [
                    InlineKeyboardButton("Create Event", callback_data="event_create"),
                    InlineKeyboardButton("Join Event", callback_data="event_join")
                ],
                [
                    InlineKeyboardButton("My Events", callback_data="event_my"),
                    InlineKeyboardButton("Settings", callback_data="wallet_settings")
                ]
            ])
        else:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect"),
                    InlineKeyboardButton("About SolMeet", callback_data="about")
                ],
                [
                    InlineKeyboardButton("What is SolMeet?", callback_data="event_info")
                ]
            ])

        await query.edit_message_text(
            text=welcome_text,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error in start callback: {e}")
        # Simplest possible fallback
        try:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect"),
                    InlineKeyboardButton("About", callback_data="about")
                ]
            ])
            await query.edit_message_text(
                "Welcome to SolMeet! Use the buttons below to navigate.",
                reply_markup=keyboard
            )
        except Exception as e2:
            logger.error(f"Fatal error in start callback fallback: {e2}")


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /settings command. Shows settings options for the user.
    """
    # Handle both message and callback query formats
    is_callback = False
    user_id = None
    
    if update.callback_query:
        is_callback = True
        query = update.callback_query
        if query.from_user:
            user_id = query.from_user.id
    elif update.message and update.effective_user:
        user_id = update.effective_user.id
    
    if not user_id:
        logger.error("No user ID found in update for settings_command")
        return
        
    user_wallet = get_wallet_by_user_id(user_id)
    
    settings_text = (
        "Settings Menu\n\n"
        "Here you can manage your wallet settings and preferences:\n\n"
        "- View your wallet recovery phrase (seed)\n"
        "- Request SOL from the Devnet faucet\n"
        "- Export wallet keyfile\n"
        "- Set notification preferences"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Wallet Settings", callback_data="wallet_settings"),
            InlineKeyboardButton("Notifications", callback_data="wallet_notifications")
        ],
        [
            InlineKeyboardButton("Security", callback_data="wallet_security"),
            InlineKeyboardButton("App Info", callback_data="app_info")
        ],
        [InlineKeyboardButton("Back to Menu", callback_data="start")]
    ])
    
    no_wallet_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect")],
        [InlineKeyboardButton("Back to Menu", callback_data="start")]
    ])
    
    try:
        if not user_wallet:
            wallet_message = "You need to connect a wallet first before accessing settings."
            if is_callback:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(
                    wallet_message,
                    reply_markup=no_wallet_keyboard
                )
            elif update.message:
                await update.message.reply_text(
                    wallet_message,
                    reply_markup=no_wallet_keyboard
                )
            return
            
        # If we got here, user has a wallet
        if is_callback:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                settings_text,
                reply_markup=keyboard
            )
        elif update.message:
            await update.message.reply_text(
                settings_text,
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Error in settings command: {e}")
        # Fallback messaging
        if is_callback and update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    "Settings menu. Use the buttons below to navigate.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Menu", callback_data="start")]])
                )
            except Exception:
                pass
        elif update.message:
            try:
                await update.message.reply_text(
                    "Settings menu. Use the buttons below to navigate.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Menu", callback_data="start")]])
                )
            except Exception:
                pass