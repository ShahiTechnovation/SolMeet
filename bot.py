#!/usr/bin/env python3
"""
SolMeet - Web3 Event Manager on Solana
A Telegram bot that enables creation and joining of Web3 events on Solana blockchain
with Here Wallet integration for wallet linking and transaction signing.
"""
import os
import logging
from dotenv import load_dotenv
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Import handlers
from handlers.start import start_command, about_command
from handlers.wallet import (
    connect_wallet_command,
    wallet_info_command,
    wallet_callback,
)
from handlers.event import (
    create_event_command,
    join_event_command,
    my_events_command, 
    handle_event_creation,
    event_callback,
    handle_text_input,
)
from handlers.faucet import faucet_command

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variables
BOT_TOKEN = os.getenv("TELEGRAM_BOT_API_KEY")
if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_API_KEY":
    logger.error("No valid TELEGRAM_BOT_API_KEY found in environment variables!")
    logger.info("Please set your Telegram Bot API key in the .env file")
    exit(1)


async def error_handler(update_obj: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors caused by updates."""
    # Cast to Update if it's the right type
    update = update_obj if isinstance(update_obj, Update) else None
    
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred while processing your request. Please try again later."
        )


def main() -> None:
    """Start the SolMeet bot."""
    # Create the Application instance
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Set up commands
    commands = [
        BotCommand("start", "Start the bot and get an introduction"),
        BotCommand("connect", "Connect your Here Wallet"),
        BotCommand("wallet", "View your wallet information"),
        BotCommand("send_create", "Create a new Solana event"),
        BotCommand("send_join", "Join an existing event"),
        BotCommand("my_events", "View your created and joined events"),
        BotCommand("faucet", "Get SOL tokens for testing on Devnet"),
    ]
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", start_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("connect", connect_wallet_command))
    application.add_handler(CommandHandler("wallet", wallet_info_command))
    application.add_handler(CommandHandler("send_create", create_event_command))
    application.add_handler(CommandHandler("send_join", join_event_command))
    application.add_handler(CommandHandler("my_events", my_events_command))
    application.add_handler(CommandHandler("faucet", faucet_command))

    # Register callback query handlers
    application.add_handler(CallbackQueryHandler(wallet_callback, pattern=r"^wallet_"))
    application.add_handler(CallbackQueryHandler(event_callback, pattern=r"^event_"))

    # Register message handlers for event flows
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_text_input
    ))

    # Register error handler
    application.add_error_handler(error_handler)

    # We'll configure the bot commands later in a post-start function
    # This avoids the async issues with set_my_commands

    # Start the Bot
    logger.info("Starting SolMeet Bot...")
    application.run_polling()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped gracefully!")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
