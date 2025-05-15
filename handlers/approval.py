"""
Approval handlers for join requests in the SolMeet bot.
"""

import logging
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from utils.join_requests import (
    add_join_request,
    approve_join_request,
    decline_join_request,
    get_request_status,
    get_event_organizer_id,
    get_event_requests,
    format_request_name
)
from utils.here_wallet import get_wallet_by_user_id
from utils.solana import format_wallet_address

logger = logging.getLogger(__name__)

async def send_join_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    event_id: str,
    user_id: int,
    user_wallet: str,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> bool:
    """
    Send a join request to the event organizer.
    
    Args:
        update: The update object
        context: The context object
        event_id: The event ID
        user_id: The user's ID
        user_wallet: The user's wallet address
        username: The user's username
        first_name: The user's first name
        last_name: The user's last name
        
    Returns:
        Success status
    """
    # Add the join request
    success = add_join_request(
        event_id=event_id,
        wallet_address=user_wallet,
        user_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name
    )
    
    if not success:
        # Check if the user already has a pending request
        status = get_request_status(event_id, user_wallet)
        
        if status == "pending":
            message = (
                f"You already have a pending request to join event {event_id}.\n\n"
                "Please wait for the organizer to approve your request."
            )
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Back to Menu", callback_data="start")]
                    ])
                )
            elif update.message:
                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Back to Menu", callback_data="start")]
                    ])
                )
            return False
        
        elif status == "approved":
            message = (
                f"You are already a participant of event {event_id}."
            )
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("My Events", callback_data="event_my")],
                        [InlineKeyboardButton("Back to Menu", callback_data="start")]
                    ])
                )
            elif update.message:
                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("My Events", callback_data="event_my")],
                        [InlineKeyboardButton("Back to Menu", callback_data="start")]
                    ])
                )
            return False
            
        # Other unknown error
        message = (
            f"There was an error sending your join request for event {event_id}."
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Try Again", callback_data="event_join")],
                    [InlineKeyboardButton("Back to Menu", callback_data="start")]
                ])
            )
        elif update.message:
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Try Again", callback_data="event_join")],
                    [InlineKeyboardButton("Back to Menu", callback_data="start")]
                ])
            )
        return False
    
    # Request added successfully, now notify the organizer
    organizer_id = get_event_organizer_id(event_id)
    
    if organizer_id:
        # Don't notify the organizer if it's the same person
        if organizer_id != user_id:
            # Send notification to organizer
            await notify_organizer_of_request(
                context=context,
                event_id=event_id,
                requester_wallet=user_wallet,
                requester_id=user_id,
                organizer_id=organizer_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
    
    # Send confirmation to user
    message = (
        f"Your request to join event {event_id} has been sent to the organizer.\n\n"
        "You will be notified when your request is approved or declined."
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Back to Menu", callback_data="start")]
            ])
        )
    elif update.message:
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Back to Menu", callback_data="start")]
            ])
        )
    
    return True


async def notify_organizer_of_request(
    context: ContextTypes.DEFAULT_TYPE,
    event_id: str,
    requester_wallet: str,
    requester_id: int,
    organizer_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> None:
    """
    Notify the event organizer of a new join request.
    
    Args:
        context: The context object
        event_id: The event ID
        requester_wallet: The requester's wallet address
        requester_id: The requester's user ID
        organizer_id: The organizer's user ID
        username: The requester's username
        first_name: The requester's first name
        last_name: The requester's last name
    """
    # Format the requester's name
    if username:
        display_name = f"@{username}"
    elif first_name:
        if last_name:
            display_name = f"{first_name} {last_name}"
        else:
            display_name = first_name
    else:
        display_name = f"User {requester_id}"
    
    # Create the notification message
    notification = (
        f"🔔 *New Join Request for Event {event_id}*\n\n"
        f"User: {display_name}\n"
        f"Wallet: `{format_wallet_address(requester_wallet)}`\n\n"
        "Would you like to approve or decline this request?"
    )
    
    # Create inline keyboard with approve/decline buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{event_id}_{requester_wallet}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"decline_{event_id}_{requester_wallet}")
        ],
        [InlineKeyboardButton("View All Requests", callback_data=f"requests_{event_id}")]
    ])
    
    try:
        # Send the notification to the organizer
        await context.bot.send_message(
            chat_id=organizer_id,
            text=notification,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        logger.info(f"Sent join request notification to organizer {organizer_id} for event {event_id}")
    except Exception as e:
        logger.error(f"Error sending join request notification: {e}")


async def approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle approval-related callback queries.
    """
    if not update.callback_query:
        logger.error("No callback query in update for approval_callback")
        return
        
    query = update.callback_query
    
    try:
        await query.answer()
        
        if not query.data:
            logger.error("No data in callback query for approval_callback")
            return
            
        if not query.from_user:
            logger.error("No user in callback query for approval_callback")
            return
            
        user_id = query.from_user.id
        
        # Parse the callback data
        parts = query.data.split("_")
        action = parts[0]
        
        if action == "approve" and len(parts) >= 3:
            # Format: approve_EVENT-ID_WALLET-ADDRESS
            event_id = parts[1]
            wallet_address = "_".join(parts[2:])  # In case the wallet has underscores
            
            # Process the approval
            success = approve_join_request(
                event_id=event_id,
                wallet_address=wallet_address,
                approved_by_user_id=user_id
            )
            
            if success:
                # Notify the requester
                requester_id = None
                requests = get_event_requests(event_id)
                
                if wallet_address in requests:
                    requester_info = requests[wallet_address]
                    requester_id = requester_info.get("user_id")
                
                if requester_id:
                    try:
                        await context.bot.send_message(
                            chat_id=requester_id,
                            text=(
                                f"🎉 Your request to join event {event_id} has been approved!\n\n"
                                "You are now a participant of this event."
                            ),
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("View My Events", callback_data="event_my")],
                                [InlineKeyboardButton("Back to Menu", callback_data="start")]
                            ])
                        )
                    except Exception as e:
                        logger.error(f"Error notifying requester of approval: {e}")
                
                # Confirm to organizer
                await query.edit_message_text(
                    f"✅ You have approved the join request for event {event_id}.\n\n"
                    f"The user with wallet {format_wallet_address(wallet_address)} has been added as a participant.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("View All Requests", callback_data=f"requests_{event_id}")],
                        [InlineKeyboardButton("Back to Menu", callback_data="start")]
                    ])
                )
            else:
                await query.edit_message_text(
                    f"❌ There was an error approving the join request for event {event_id}.\n\n"
                    "Please try again later.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Back to Menu", callback_data="start")]
                    ])
                )
                
        elif action == "decline" and len(parts) >= 3:
            # Format: decline_EVENT-ID_WALLET-ADDRESS
            event_id = parts[1]
            wallet_address = "_".join(parts[2:])  # In case the wallet has underscores
            
            # Process the decline
            success = decline_join_request(
                event_id=event_id,
                wallet_address=wallet_address,
                declined_by_user_id=user_id
            )
            
            if success:
                # Notify the requester
                requester_id = None
                requests = get_event_requests(event_id)
                
                if wallet_address in requests:
                    requester_info = requests[wallet_address]
                    requester_id = requester_info.get("user_id")
                
                if requester_id:
                    try:
                        await context.bot.send_message(
                            chat_id=requester_id,
                            text=(
                                f"Your request to join event {event_id} has been declined by the organizer.\n\n"
                                "You can try joining a different event or create your own."
                            ),
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("Find Events", callback_data="event_list")],
                                [InlineKeyboardButton("Create Event", callback_data="event_create")],
                                [InlineKeyboardButton("Back to Menu", callback_data="start")]
                            ])
                        )
                    except Exception as e:
                        logger.error(f"Error notifying requester of decline: {e}")
                
                # Confirm to organizer
                await query.edit_message_text(
                    f"❌ You have declined the join request for event {event_id}.\n\n"
                    f"The user with wallet {format_wallet_address(wallet_address)} has been notified.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("View All Requests", callback_data=f"requests_{event_id}")],
                        [InlineKeyboardButton("Back to Menu", callback_data="start")]
                    ])
                )
            else:
                await query.edit_message_text(
                    f"❌ There was an error declining the join request for event {event_id}.\n\n"
                    "Please try again later.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Back to Menu", callback_data="start")]
                    ])
                )
                
        elif action == "requests" and len(parts) >= 2:
            # Format: requests_EVENT-ID
            event_id = parts[1]
            
            # Get all pending requests for this event
            requests = get_event_requests(event_id)
            
            if not requests:
                await query.edit_message_text(
                    f"There are no pending join requests for event {event_id}.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Back to Events", callback_data="event_my")],
                        [InlineKeyboardButton("Back to Menu", callback_data="start")]
                    ])
                )
                return
            
            # Create a list of requests with approve/decline buttons for each
            message = f"Pending Join Requests for Event {event_id}:\n\n"
            
            keyboard = []
            for wallet, info in requests.items():
                name = format_request_name(info)
                message += f"• {name} ({format_wallet_address(wallet)})\n"
                
                # Add approve/decline buttons for this request
                keyboard.append([
                    InlineKeyboardButton(f"✅ Approve {name}", callback_data=f"approve_{event_id}_{wallet}"),
                    InlineKeyboardButton("❌ Decline", callback_data=f"decline_{event_id}_{wallet}")
                ])
            
            keyboard.append([InlineKeyboardButton("Back to Menu", callback_data="start")])
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.error(f"Error in approval callback: {e}")
        if update.callback_query and update.callback_query.message:
            try:
                await update.callback_query.message.reply_text(
                    "An error occurred while processing your request. Please try again later.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back to Menu", callback_data="start")]])
                )
            except Exception:
                pass