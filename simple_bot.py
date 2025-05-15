#!/usr/bin/env python3
"""
SolMeet - Web3 Event Manager on Solana
A Telegram bot that enables creation and joining of Web3 events on Solana blockchain
with Here Wallet integration for wallet linking and transaction signing.
"""
import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(f"Hi {user.first_name}! I am SolMeet Bot. Welcome to Web3 Event Manager on Solana.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "Available commands:\n"
        "/start - Start the bot and get a welcome message\n"
        "/help - Show this help message\n"
        "/about - Learn more about SolMeet Bot"
    )
    await update.message.reply_text(help_text)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /about is issued."""
    about_text = (
        "SolMeet - Web3 Event Manager on Solana\n\n"
        "A Telegram bot that enables creation and joining of Web3 events on Solana blockchain "
        "with Here Wallet integration for wallet linking and transaction signing."
    )
    await update.message.reply_text(about_text)

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))

    # Run the bot until the user presses Ctrl-C
    logger.info("Starting SolMeet Bot...")
    application.run_polling()
    logger.info("Bot stopped")

if __name__ == "__main__":
    main()