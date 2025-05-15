"""
Wallet connection and management handlers for the SolMeet bot.
"""

import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from utils.here_wallet import (
    generate_connect_url, get_wallet_by_user_id, 
    create_wallet_for_user, get_wallet_info
)
from utils.solana import get_sol_balance, format_wallet_address, request_airdrop
from utils.keyboard import get_main_keyboard

logger = logging.getLogger(__name__)


async def connect_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /connect command. Helps users create a new wallet.
    """
    user_id = update.effective_user.id
    user_wallet = get_wallet_by_user_id(user_id)
    
    if user_wallet:
        # User already has a connected wallet
        await update.message.reply_text(
            f"You already have a wallet connected:\n\n"
            f"*Address:* `{format_wallet_address(user_wallet)}`\n\n"
            "You can view your wallet details with /wallet.",
            parse_mode="Markdown",
            reply_markup=get_wallet_connected_keyboard()
        )
    else:
        # User needs to create a wallet
        await update.message.reply_text(
            "To create or join events, you need a Solana wallet.\n\n"
            "*Create a new wallet:*\n"
            "1. Click the button below to create a wallet right here\n"
            "2. We'll generate a new wallet for you on Solana Devnet\n"
            "3. Make sure to save your recovery phrase!\n",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Create a new wallet", callback_data="wallet_create_new")],
                [InlineKeyboardButton("What is a wallet?", callback_data="wallet_learn")]
            ])
        )


async def wallet_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /wallet command. Shows user's wallet information.
    """
    user_id = update.effective_user.id
    user_wallet = get_wallet_by_user_id(user_id)
    
    if not user_wallet:
        await update.message.reply_text(
            "You don't have a wallet yet. Use /connect to create a new Solana wallet.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Create a new wallet", callback_data="wallet_create_new")]
            ])
        )
        return
    
    try:
        sol_balance = await get_sol_balance(user_wallet)
        
        # Get wallet details including private key and mnemonic
        wallet_info = get_wallet_info(user_wallet)
        if wallet_info:
            # Show complete wallet details with private key and mnemonic
            private_key = wallet_info.get("private_key", "Not available")
            mnemonic = wallet_info.get("mnemonic", "Not available")
            
            wallet_text = (
                "*Your Wallet Details*\n\n"
                f"*Address:* `{format_wallet_address(user_wallet)}`\n"
                f"*Balance:* {sol_balance} SOL (Devnet)\n"
                f"*Recovery Phrase:* `{mnemonic}`\n"
                f"*Private Key:* `{private_key}`\n\n"
                "⚠️ *IMPORTANT:* Save this recovery phrase and private key somewhere safe.\n"
                "Never share these with anyone! They provide full access to your wallet."
            )
        else:
            wallet_text = (
                "*Your Wallet Details*\n\n"
                f"*Address:* `{format_wallet_address(user_wallet)}`\n"
                f"*Balance:* {sol_balance} SOL (Devnet)\n\n"
                "You can use this wallet to create and join events on Solana."
            )
        
        await update.message.reply_text(
            wallet_text,
            parse_mode="Markdown",
            reply_markup=get_wallet_actions_keyboard(user_wallet)
        )
    except Exception as e:
        logger.error(f"Error fetching wallet info: {e}")
        await update.message.reply_text(
            "There was an error fetching your wallet information. Please try again later.",
            reply_markup=get_main_keyboard()
        )


async def wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for wallet-related callback queries.
    """
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    try:
        # Special case handlers
        if callback_data == "wallet_create_new":
            # Direct handler for wallet creation
            await handle_wallet_creation(query, user_id)
            return
            
        # For standard wallet actions with wallet_action format
        if not callback_data.startswith("wallet_"):
            logger.warning(f"Invalid wallet callback format: {callback_data}")
            return
            
        # Extract the action part
        parts = callback_data.split("_")
        if len(parts) < 2:
            logger.warning(f"Invalid callback data format: {callback_data}")
            return
            
        action = parts[1]
        
        if action == "connect":
            # Show connect wallet options
            await query.message.reply_text(
                "To create or join events, you need a Solana wallet.\n\n"
                "*Create a new wallet:*\n"
                "1. Click the button below to create a wallet right here\n"
                "2. We'll generate a new wallet for you on Solana Devnet\n"
                "3. Make sure to save your recovery phrase!\n",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Create a new wallet", callback_data="wallet_create_new")],
                    [InlineKeyboardButton("What is a wallet?", callback_data="wallet_learn")]
                ])
            )
        elif action == "info":
            # Show wallet info
            await wallet_info_command(update, context)
        elif action == "faucet":
            # Request SOL from faucet
            from handlers.faucet import faucet_command
            await faucet_command(update, context)
        elif action == "learn":
            # Learn about wallets
            await query.message.reply_text(
                "*What is a Solana Wallet?*\n\n"
                "A Solana wallet is your identity on the Solana blockchain. It consists of:\n\n"
                "• An *address* - This is like your username on the blockchain\n"
                "• A *recovery phrase* - A list of words that gives access to your wallet\n\n"
                "In this bot, we create Devnet wallets for testing. These are not for real money.\n"
                "Your recovery phrase is very important - save it somewhere safe!",
                parse_mode="Markdown"
            )
        else:
            logger.warning(f"Unknown wallet action: {action}")
    except Exception as e:
        logger.error(f"Error in wallet callback: {e}")
        await query.message.reply_text(
            "Sorry, something went wrong. Please try again.",
            reply_markup=get_main_keyboard()
        )


async def handle_wallet_creation(query, user_id: int):
    """Handle the wallet creation process."""
    await query.message.reply_text("Creating your new Solana wallet... Please wait.")
    
    try:
        # Create a new wallet
        success, wallet_address, wallet_info = create_wallet_for_user(user_id)
        
        if not success or not wallet_address or not wallet_info:
            await query.message.reply_text(
                "❌ Sorry, there was an error creating your wallet. Please try again later."
            )
            return
            
        # Get the mnemonic from wallet info
        mnemonic = wallet_info.get("mnemonic", "")
        
        # Format the wallet address
        formatted_address = format_wallet_address(wallet_address)
        
        # Get the private key to show to the user
        private_key = wallet_info.get("private_key", "Not available")
            
        # Send the success message with all details
        await query.message.reply_text(
            f"✅ Your new Solana wallet has been created!\n\n"
            f"*Address:* `{formatted_address}`\n\n"
            f"*Recovery Phrase (SAVE THIS!):*\n`{mnemonic}`\n\n"
            f"*Private Key:*\n`{private_key}`\n\n"
            f"⚠️ *WARNING:* Never share your recovery phrase or private key with anyone!\n"
            f"Write them down and keep them safe. These are the only ways to recover your wallet.",
            parse_mode="Markdown",
            reply_markup=get_wallet_connected_keyboard()
        )
        
        # Request SOL from the faucet for new wallets
        try:
            tx_sig = await request_airdrop(wallet_address, 1.0)
            await query.message.reply_text(
                f"✅ Also requested 1 SOL from the Devnet faucet for you!\n"
                f"Transaction: `{tx_sig}`\n\n"
                f"Use /wallet to see your balance.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error requesting airdrop: {e}")
            await query.message.reply_text(
                "Note: You'll need SOL for transactions. Use /faucet to get Devnet SOL."
            )
    except Exception as e:
        logger.error(f"Error creating wallet: {e}")
        await query.message.reply_text(
            "❌ Sorry, there was an error creating your wallet. Please try again later."
        )


def get_wallet_connected_keyboard() -> InlineKeyboardMarkup:
    """
    Returns a keyboard for users who have already connected their wallet.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("View Wallet", callback_data="wallet_info"),
            InlineKeyboardButton("Get Devnet SOL", callback_data="wallet_faucet")
        ],
        [InlineKeyboardButton("Back to Menu", callback_data="start")]
    ])


def get_wallet_actions_keyboard(wallet_address: str) -> InlineKeyboardMarkup:
    """
    Returns a keyboard with wallet action options.
    """
    explorer_url = f"https://explorer.solana.com/address/{wallet_address}?cluster=devnet"
    
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("View on Explorer", url=explorer_url),
            InlineKeyboardButton("Get Devnet SOL", callback_data="wallet_faucet")
        ],
        [
            InlineKeyboardButton("Create Event", callback_data="event_create"),
            InlineKeyboardButton("Join Event", callback_data="event_join")
        ],
        [InlineKeyboardButton("Back to Menu", callback_data="start")]
    ])
