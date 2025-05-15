"""
Wallet connection and management handlers for the SolMeet bot.
"""

import logging
import json
from typing import Dict, Any, Optional, Tuple

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram._message import Message

from utils.here_wallet import (
    generate_connect_url,
    get_wallet_by_user_id,
    create_wallet_for_user,
    get_user_wallets,
    link_wallet_to_user,
)
from utils.wallet_creator import get_wallet_info
from utils.solana import get_sol_balance, format_wallet_address
from utils.qr import generate_wallet_qr
from utils import (
    safe_message_reply, 
    safe_photo_reply, 
    safe_edit_message_text, 
    safe_answer,
    safe_get_chat_id
)

logger = logging.getLogger(__name__)

async def connect_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /connect command. Helps users create a new wallet.
    """
    if not update.message:
        logger.error("No message in update for connect_wallet_command")
        return

    if not update.effective_user:
        logger.error("No user in update for connect_wallet_command")
        return

    user_id = update.effective_user.id
    
    # Check if they already have a wallet
    existing_wallet = get_wallet_by_user_id(user_id)
    if existing_wallet:
        await safe_message_reply(
            update.message,
            f"You already have a connected wallet: `{format_wallet_address(existing_wallet)}`\n\n"
            "What would you like to do with your wallet?",
            parse_mode="Markdown",
            reply_markup=get_wallet_actions_keyboard(existing_wallet)
        )
        return
    
    # New user without a wallet
    connect_url = generate_connect_url(user_id)
    
    await safe_message_reply(
        update.message,
        "Let's connect your wallet to SolMeet!\n\n"
        "You have two options:\n"
        "1️⃣ Create a new Solana wallet directly in the bot (recommended for beginners)\n"
        "2️⃣ Import an existing Here Wallet\n\n"
        "What would you like to do?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Create New Wallet", callback_data="wallet_create")],
            [InlineKeyboardButton("View Available Wallets", callback_data="wallet_list")],
            [InlineKeyboardButton("Back to Menu", callback_data="start")]
        ])
    )


async def wallet_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /wallet command. Shows user's wallet information.
    """
    if not update.message:
        logger.error("No message in update for wallet_info_command")
        return

    if not update.effective_user:
        logger.error("No user in update for wallet_info_command")
        return

    user_id = update.effective_user.id
    user_wallet = get_wallet_by_user_id(user_id)
    
    if not user_wallet:
        await safe_message_reply(
            update.message,
            "You don't have a wallet connected yet. Would you like to create one?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect")],
                [InlineKeyboardButton("Back to Menu", callback_data="start")]
            ])
        )
        return
    
    try:
        # Get wallet balance
        balance = await get_sol_balance(user_wallet)
        
        info_text = (
            "🔐 *Your Wallet*\n\n"
            f"Address: `{user_wallet}`\n\n"
            f"Balance: *{balance} SOL*\n\n"
            "This is a Solana wallet on Devnet, meant for testing and development."
        )
        
        await safe_message_reply(
            update.message,
            info_text,
            parse_mode="Markdown",
            reply_markup=get_wallet_actions_keyboard(user_wallet)
        )
    except Exception as e:
        logger.error(f"Error fetching wallet info: {e}")
        await safe_message_reply(
            update.message,
            "There was an error fetching your wallet information. Please try again later.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Back to Menu", callback_data="start")]
            ])
        )


async def wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for wallet-related callback queries.
    """
    if not update.callback_query:
        logger.error("No callback query in update for wallet_callback")
        return
        
    query = update.callback_query
    
    try:
        await query.answer()
        
        if not query.from_user:
            logger.error("No user in callback query for wallet_callback")
            return
            
        user_id = query.from_user.id
        callback_data = query.data
        
        if not callback_data:
            logger.error("No data in callback query for wallet_callback")
            return
            
        logger.info(f"Processing wallet callback: {callback_data}")
        
        if callback_data.startswith("wallet_connect"):
            # This is the same as the /connect command
            connect_url = generate_connect_url(user_id)
            
            await query.edit_message_text(
                "Let's connect your wallet to SolMeet!\n\n"
                "You have two options:\n"
                "1️⃣ Create a new Solana wallet directly in the bot (recommended for beginners)\n"
                "2️⃣ Import an existing Here Wallet\n\n"
                "What would you like to do?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Create New Wallet", callback_data="wallet_create")],
                    [InlineKeyboardButton("View Available Wallets", callback_data="wallet_list")],
                    [InlineKeyboardButton("Back to Menu", callback_data="start")]
                ])
            )
        
        elif callback_data == "wallet_create":
            # Handle wallet creation
            await handle_wallet_creation(query, user_id)
            
        elif callback_data == "wallet_list":
            # Show list of available wallets
            available_wallets = get_user_wallets()
            
            if not available_wallets:
                if not query.message:
                    logger.error("No message in callback query for wallet_list")
                    return
                
                await safe_message_reply(
                    query.message,
                    "No wallets are currently available to claim. Try creating a new wallet.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Create New Wallet", callback_data="wallet_create")],
                        [InlineKeyboardButton("Back to Menu", callback_data="start")]
                    ])
                )
                return
                
            wallet_buttons = []
            for address, name in available_wallets.items():
                wallet_buttons.append([InlineKeyboardButton(
                    f"{name} ({format_wallet_address(address)})",
                    callback_data=f"wallet_select_{address}"
                )])
            
            wallet_buttons.append([InlineKeyboardButton("Back", callback_data="wallet_connect")])
            
            await query.edit_message_text(
                "Here are the available wallets you can use.\n"
                "Select one to connect to your account:",
                reply_markup=InlineKeyboardMarkup(wallet_buttons)
            )
            
        elif callback_data.startswith("wallet_select_"):
            # User selected a wallet to connect
            wallet_address = callback_data.split("_", 2)[2]
            if link_wallet_to_user(user_id, wallet_address):
                if not query.message:
                    logger.error("No message in callback query for wallet_select")
                    return
                
                await safe_message_reply(
                    query.message,
                    f"Successfully connected wallet: `{format_wallet_address(wallet_address)}`\n\n"
                    "You can now create and join events with this wallet.",
                    parse_mode="Markdown",
                    reply_markup=get_wallet_connected_keyboard()
                )
            else:
                if not query.message:
                    logger.error("No message in callback query for wallet_select")
                    return
                
                await safe_message_reply(
                    query.message,
                    "There was an error connecting this wallet. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Try Again", callback_data="wallet_connect")]])
                )
                
        elif callback_data == "wallet_info":
            # Show wallet info
            user_wallet = get_wallet_by_user_id(user_id)
            if not user_wallet:
                if not query.message:
                    logger.error("No message in callback query for wallet_info")
                    return
                
                await safe_message_reply(
                    query.message,
                    "You don't have a wallet connected."
                )
                return
            
            try:
                # Get wallet balance
                balance = await get_sol_balance(user_wallet)
                
                info_text = (
                    "🔐 *Your Wallet*\n\n"
                    f"Address: `{user_wallet}`\n\n"
                    f"Balance: *{balance} SOL*\n\n"
                    "This is a Solana wallet on Devnet, meant for testing and development."
                )
                
                await safe_edit_message_text(
                    query,
                    info_text,
                    parse_mode="Markdown",
                    reply_markup=get_wallet_actions_keyboard(user_wallet)
                )
            except Exception as e:
                logger.error(f"Error fetching wallet info: {e}")
                if not query.message:
                    logger.error("No message in callback query when handling error")
                    return
                
                await safe_message_reply(
                    query.message,
                    "There was an error fetching your wallet information. Please try again later.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Back to Menu", callback_data="start")]
                    ])
                )
                
        elif callback_data == "wallet_qr":
            user_wallet = get_wallet_by_user_id(user_id)
            if not user_wallet:
                if not query.message:
                    logger.error("No message in callback query for wallet_qr")
                    return
                    
                await safe_message_reply(query.message, "You don't have a wallet connected.")
                return
                
            qr_path = generate_wallet_qr(user_wallet)
            if not qr_path:
                if not query.message:
                    logger.error("No message in callback query for wallet_qr")
                    return
                    
                await safe_message_reply(query.message, "Could not generate QR code. Please try again.")
                return
                
            if not query.message:
                logger.error("No message in callback query for wallet_qr")
                return
                
            await safe_photo_reply(
                query.message,
                photo=open(qr_path, "rb"),
                caption=f"QR Code for wallet: `{format_wallet_address(user_wallet)}`\n\n"
                "Scan this QR code to see your wallet address.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Back to Wallet", callback_data="wallet_info")],
                    [InlineKeyboardButton("Back to Menu", callback_data="start")]
                ])
            )
            
        elif callback_data == "wallet_settings":
            # Show wallet settings
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("View Seed Phrase", callback_data="wallet_seed"),
                    InlineKeyboardButton("Export Wallet", callback_data="wallet_export")
                ],
                [
                    InlineKeyboardButton("Notifications", callback_data="wallet_notifications"),
                    InlineKeyboardButton("Security Tips", callback_data="wallet_security")
                ],
                [InlineKeyboardButton("Back to Wallet", callback_data="wallet_info")],
                [InlineKeyboardButton("Back to Menu", callback_data="start")]
            ])
            
            await query.edit_message_text(
                "*Wallet Settings*\n\n"
                "Manage your wallet settings and security options:\n\n"
                "• View your wallet's recovery seed phrase\n"
                "• Export your private key\n"
                "• Configure notification preferences\n"
                "• Get security recommendations",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
        elif callback_data == "wallet_seed":
            user_wallet = get_wallet_by_user_id(user_id)
            if not user_wallet:
                if not query.message:
                    logger.error("No message in callback query for wallet_seed")
                    return
                    
                await safe_message_reply(query.message, "You don't have a wallet connected.")
                return
                
            wallet_info = get_wallet_info(user_wallet)
            if not wallet_info:
                if not query.message:
                    logger.error("No message in callback query for wallet_seed")
                    return
                    
                await safe_message_reply(query.message, "Could not retrieve wallet details.")
                return
                
            mnemonic = wallet_info.get("mnemonic", "Not available")
            
            if not query.message:
                logger.error("No message in callback query for wallet_seed")
                return
                
            await safe_message_reply(
                query.message,
                "*Your Recovery Seed Phrase*\n\n"
                f"`{mnemonic}`\n\n"
                "This seed phrase gives complete access to your wallet. Keep it safe!\n\n"
                "⚠️ *WARNING*: Never share this with anyone!\n"
                "Anyone with this phrase can access your wallet.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Back to Settings", callback_data="wallet_settings")],
                    [InlineKeyboardButton("Back to Menu", callback_data="start")]
                ])
            )
        elif callback_data == "wallet_export":
            user_wallet = get_wallet_by_user_id(user_id)
            if not user_wallet:
                if not query.message:
                    logger.error("No message in callback query for wallet_export")
                    return
                    
                await safe_message_reply(query.message, "You don't have a wallet connected.")
                return
                
            wallet_info = get_wallet_info(user_wallet)
            if not wallet_info:
                if not query.message:
                    logger.error("No message in callback query for wallet_export")
                    return
                    
                await safe_message_reply(query.message, "Could not retrieve wallet details.")
                return
                
            private_key = wallet_info.get("private_key", "Not available")
            
            if not query.message:
                logger.error("No message in callback query for wallet_export")
                return
                
            await safe_message_reply(
                query.message,
                "*Your Private Key*\n\n"
                f"`{private_key}`\n\n"
                "You can use this private key to import your wallet into other Solana wallets.\n"
                "⚠️ *WARNING*: Never share this with anyone!\n"
                "This key gives complete access to your wallet.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Back to Settings", callback_data="wallet_settings")],
                    [InlineKeyboardButton("Back to Menu", callback_data="start")]
                ])
            )
        elif callback_data == "wallet_notifications":
            # Simple notifications preferences
            notification_text = (
                "*Notification Settings*\n\n"
                "Choose which notifications you want to receive:\n\n"
                "• Event creation confirmations\n"
                "• New event participants\n"
                "• Faucet request confirmations\n"
                "• Transaction confirmations"
            )
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Enable All", callback_data="wallet_notify_enable_all"),
                    InlineKeyboardButton("Disable All", callback_data="wallet_notify_disable_all")
                ],
                [
                    InlineKeyboardButton("Event Updates Only", callback_data="wallet_notify_events"),
                    InlineKeyboardButton("Transactions Only", callback_data="wallet_notify_transactions")
                ],
                [InlineKeyboardButton("Back to Settings", callback_data="wallet_settings")],
                [InlineKeyboardButton("Back to Menu", callback_data="start")]
            ])
            
            await query.edit_message_text(
                notification_text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        elif callback_data == "wallet_security":
            security_text = (
                "*Wallet Security Tips*\n\n"
                "Follow these best practices to keep your crypto wallet safe:\n\n"
                "• Never share your seed phrase or private key with anyone\n"
                "• Store your recovery phrase offline in a secure location\n"
                "• Be cautious of phishing attempts and fake websites\n"
                "• Use hardware wallets for large amounts\n"
                "• Enable two-factor authentication where available\n"
                "• Regularly update your wallet software\n\n"
                "Remember: This is a Devnet wallet for testing purposes only."
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Back to Settings", callback_data="wallet_settings")],
                [InlineKeyboardButton("Back to Menu", callback_data="start")]
            ])
            
            await query.edit_message_text(
                security_text,
                parse_mode="Markdown", 
                reply_markup=keyboard
            )
        elif callback_data.startswith("wallet_notify_"):
            # Simulated notification preference setting
            option = callback_data.replace("wallet_notify_", "")
            
            confirmation_text = ""
            if option == "enable_all":
                confirmation_text = "You will now receive all notifications."
            elif option == "disable_all":
                confirmation_text = "All notifications have been disabled."
            elif option == "events":
                confirmation_text = "You will now receive event update notifications only."
            elif option == "transactions":
                confirmation_text = "You will now receive transaction notifications only."
                
            await safe_edit_message_text(
                query,
                f"*Notification Settings Updated*\n\n{confirmation_text}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Back to Settings", callback_data="wallet_settings")],
                    [InlineKeyboardButton("Back to Menu", callback_data="start")]
                ])
            )
        else:
            logger.warning(f"Unknown wallet action: {callback_data}")
    except Exception as e:
        logger.error(f"Error in wallet callback: {e}")
        # Try to respond even in case of error
        try:
            if update.callback_query and update.callback_query.message:
                await safe_message_reply(
                    update.callback_query.message,
                    "Sorry, an error occurred processing your request. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Menu", callback_data="start")]])
                )
        except Exception:
            pass


async def handle_wallet_creation(query, user_id: int):
    """Handle the wallet creation process."""
    if query is None:
        logger.error("Query is None in handle_wallet_creation")
        return
        
    if query.message is None:
        logger.error("Message is None in handle_wallet_creation")
        return
        
    # First, tell the user we're creating a wallet
    await safe_edit_message_text(
        query,
        "Creating a new Solana wallet for you...\n"
        "This will take a few seconds.",
        reply_markup=None
    )
    
    # Attempt to create a wallet
    success, wallet_address, wallet_info = create_wallet_for_user(user_id)
    
    if not success or not wallet_address:
        await safe_message_reply(
            query.message,
            "There was an error creating your wallet. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Menu", callback_data="start")]])
        )
        return
    
    # We successfully created a wallet!
    reply_text = (
        "✅ Wallet created successfully!\n\n"
        f"Your wallet address: `{wallet_address}`\n\n"
        "I'll get you some SOL from the Devnet faucet to get started..."
    )
    
    await safe_message_reply(
        query.message,
        reply_text,
        parse_mode="Markdown",
        reply_markup=None
    )
    
    # Try to add some initial SOL from the faucet
    # This is handled in create_wallet_for_user already
    
    # Show the wallet info and options
    try:
        balance = await get_sol_balance(wallet_address)
        
        info_text = (
            "🔐 *Your New Wallet*\n\n"
            f"Address: `{wallet_address}`\n\n"
            f"Balance: *{balance} SOL*\n\n"
            "This is a Solana wallet on Devnet, meant for testing and development.\n\n"
            "What would you like to do next?"
        )
        
        await query.message.reply_text(
            info_text,
            parse_mode="Markdown",
            reply_markup=get_wallet_connected_keyboard()
        )
    except Exception as e:
        logger.error(f"Error showing new wallet: {e}")
        await query.message.reply_text(
            f"Wallet created successfully: `{format_wallet_address(wallet_address)}`\n\n"
            "You can now create and join events with this wallet.",
            parse_mode="Markdown",
            reply_markup=get_wallet_connected_keyboard()
        )


def get_wallet_connected_keyboard() -> InlineKeyboardMarkup:
    """
    Returns a keyboard for users who have already connected their wallet.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Create Event", callback_data="event_create"),
            InlineKeyboardButton("Join Event", callback_data="event_join")
        ],
        [
            InlineKeyboardButton("Wallet Info", callback_data="wallet_info"),
            InlineKeyboardButton("My Events", callback_data="event_my")
        ],
        [InlineKeyboardButton("Back to Menu", callback_data="start")]
    ])


def get_wallet_actions_keyboard(wallet_address: str) -> InlineKeyboardMarkup:
    """
    Returns a keyboard with wallet action options.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("View QR Code", callback_data="wallet_qr"),
            InlineKeyboardButton("Get SOL (Faucet)", callback_data="wallet_faucet")
        ],
        [
            InlineKeyboardButton("Settings", callback_data="wallet_settings"), 
            InlineKeyboardButton("View on Explorer", url=f"https://explorer.solana.com/address/{wallet_address}?cluster=devnet")
        ],
        [InlineKeyboardButton("Back to Menu", callback_data="start")]
    ])