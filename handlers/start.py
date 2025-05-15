"""
Start command handlers for the SolMeet bot.
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from utils.keyboard import get_main_keyboard
from utils.here_wallet import get_wallet_by_user_id


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /start command. Introduces the bot and provides initial guidance.
    """
    user = update.effective_user
    
    welcome_text = (
        f"Hello, {user.first_name}! Welcome to *SolMeet* - your Web3 Event Manager on Solana.\n\n"
        "I can help you create and join on-chain events using your Solana wallet.\n\n"
        "*What can you do with SolMeet?*\n"
        "- Create events with name, venue, description, and attendee limits\n"
        "- Join events with unique codes or links and claim your attendance NFT\n"
        "- Connect securely with Here Wallet - no private keys stored\n"
        "- Track your created and joined events on-chain\n\n"
        "*Getting Started:*\n"
        "1. First, connect your wallet with /connect\n"
        "2. Create an event with /send_create or join one with /send_join\n"
        "3. View your events with /my_events\n\n"
        "Need SOL tokens for testing? Use /faucet to get some on Devnet."
    )

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

    await update.message.reply_text(
        text=welcome_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for showing information about the SolMeet bot.
    """
    about_text = (
        "*SolMeet | Web3 Event Bot*\n\n"
        "SolMeet is a Telegram bot for creating and joining events on the Solana blockchain.\n\n"
        "*Key Features:*\n"
        "- Create on-chain events with custom parameters\n"
        "- Join events with unique codes and claim NFT attestations\n"
        "- Secure wallet integration via Here Wallet\n"
        "- One-claim-per-user verification\n"
        "- Track all your events in one place\n"
        "- Quick access to transaction details via Solana Explorer\n\n"
        "*Technical Stack:*\n"
        "- Runs on Solana Devnet\n"
        "- Anchor smart contract for on-chain operations\n"
        "- Secure transaction signing through Here Wallet\n"
        "- No private keys are ever stored by the bot\n\n"
        "Perfect for hackathons, meetups, conferences, and community events!"
    )

    # Handle both message replies and callback queries
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=about_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            text=about_text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )


async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for 'start' callback query (back to menu button).
    """
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    user_wallet = get_wallet_by_user_id(user_id)
    
    welcome_text = (
        f"Hello, {user.first_name}! Welcome to *SolMeet* - your Web3 Event Manager on Solana.\n\n"
        "I can help you create and join on-chain events using your Solana wallet.\n\n"
        "*What can you do with SolMeet?*\n"
        "- Create events with name, venue, description, and attendee limits\n"
        "- Join events with unique codes or links and claim your attendance NFT\n"
        "- Connect securely with Here Wallet - no private keys stored\n"
        "- Track your created and joined events on-chain\n\n"
        "*Getting Started:*\n"
        "1. First, connect your wallet with /connect\n"
        "2. Create an event with /send_create or join one with /send_join\n"
        "3. View your events with /my_events\n\n"
        "Need SOL tokens for testing? Use /faucet to get some on Devnet."
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
        reply_markup=keyboard,
        parse_mode="Markdown"
    )