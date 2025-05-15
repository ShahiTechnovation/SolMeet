"""
Custom keyboard utilities for the SolMeet bot.
"""

from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard() -> InlineKeyboardMarkup:
    """
    Returns the main menu keyboard with common actions.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect"),
            InlineKeyboardButton("My Wallet", callback_data="wallet_info")
        ],
        [
            InlineKeyboardButton("Create Event", callback_data="event_create"),
            InlineKeyboardButton("Join Event", callback_data="event_join")
        ],
        [
            InlineKeyboardButton("My Events", callback_data="event_list_mine"),
            InlineKeyboardButton("Get Devnet SOL", callback_data="wallet_faucet")
        ]
    ])


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Returns a keyboard with just a cancel button for flows that can be canceled.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Cancel", callback_data="event_cancel")]
    ])


def get_wallet_required_keyboard() -> InlineKeyboardMarkup:
    """
    Returns a keyboard for prompting users to connect their wallet.
    """
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect")],
        [InlineKeyboardButton("Back to Menu", callback_data="start")]
    ])


def get_event_actions_keyboard(event_id: str) -> InlineKeyboardMarkup:
    """
    Returns a keyboard with actions for a specific event.
    """
    view_url = f"https://explorer.solana.com/address/{event_id}?cluster=devnet"
    
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("View Details", callback_data=f"event_view_{event_id}"),
            InlineKeyboardButton("View on Explorer", url=view_url)
        ],
        [
            InlineKeyboardButton("Share Event", callback_data=f"event_share_{event_id}"),
            InlineKeyboardButton("Back to Events", callback_data="event_list_mine")
        ]
    ])
