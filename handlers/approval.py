"""
Approval handlers for join requests in the SolMeet bot.
"""

import logging
import os
import asyncio
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils.join_requests import (
    add_join_request,
    approve_join_request,
    decline_join_request,
    format_requests_list,
    get_event_by_id,
    get_event_organizer_id,
    get_event_requests,
    get_request_status,
    format_request_name,
)
from utils.participants import add_event_participant, count_event_participants
from utils.solana import join_event_onchain, format_wallet_address
from utils.qr import generate_join_qr

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
    try:
        # Check if the user has already sent a request for this event
        request_status = get_request_status(event_id, user_wallet)
        
        if request_status == "approved":
            if update.message:
                await update.message.reply_text(
                    f"✅ You've already been approved for event {event_id}!"
                )
            return True
            
        if request_status == "pending":
            if update.message:
                await update.message.reply_text(
                    f"⌛ Your request to join event {event_id} is still pending approval."
                )
            return True
            
        if request_status == "declined":
            if update.message:
                await update.message.reply_text(
                    f"❌ Your request to join event {event_id} was declined by the organizer."
                )
            return False
        
        # Add the join request
        added = add_join_request(
            event_id=event_id,
            wallet_address=user_wallet,
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        
        if added:
            # Get the event organizer's user ID
            organizer_id = get_event_organizer_id(event_id)
            
            if organizer_id:
                # Notify the organizer
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
                
                return True
            else:
                logger.error(f"Could not find organizer for event {event_id}")
                if update.message:
                    await update.message.reply_text(
                        f"❌ Could not find the organizer for event {event_id}. Please try again later."
                    )
                return False
        else:
            logger.error(f"Could not add join request for event {event_id}")
            if update.message:
                await update.message.reply_text(
                    f"❌ There was an error sending your join request. Please try again later."
                )
            return False
            
    except Exception as e:
        logger.error(f"Error sending join request: {e}")
        if update.message:
            await update.message.reply_text(
                f"❌ Error sending join request: {str(e)}"
            )
        return False

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
    Notify the event organizer of a new join request with improved one-click approval UI.
    
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

    try:
        # Format the user's name for display
        if username:
            display_name = f"@{username}"
        elif first_name:
            display_name = first_name
            if last_name:
                display_name += f" {last_name}"
        else:
            display_name = f"User {requester_id}"
        
        # Get event details from join requests system
        
        event = get_event_by_id(event_id)
        if not event:
            logger.warning(f"Could not find event {event_id} details for notification")
            event_name = "Unnamed Event"
            event_date = "Date not set"
            event_venue = "Venue not set"
        else:
            event_name = event.get("name", "Unnamed Event")
            event_date = event.get("date", "Date not set")
            event_venue = event.get("venue", "Venue not set")
        
        # Get participant count information
        participant_count = count_event_participants(event_id)
        max_participants = event.get("max_participants", "∞") if event else "∞"
        
        # Create an improved keyboard with approval/decline buttons
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{event_id}_{requester_wallet}"),
                InlineKeyboardButton("❌ Decline", callback_data=f"decline_{event_id}_{requester_wallet}")
            ],
            [
                InlineKeyboardButton("👥 View All Requests", callback_data=f"requests_{event_id}")
            ]
        ])
        
        # Format wallet address for display
        from utils.solana import format_wallet_address
        short_wallet = format_wallet_address(requester_wallet)
        
        # Send the enhanced notification to the organizer
        await context.bot.send_message(
            chat_id=organizer_id,
            text=(
                f"🔔 *New Join Request*\n\n"
                f"*{display_name}* wants to join your event:\n"
                f"*{event_name}*\n\n"
                f"📅 {event_date}\n"
                f"📍 {event_venue}\n"
                f"👥 Participants: {participant_count}/{max_participants}\n\n"
                f"Wallet: `{short_wallet}`\n\n"
                f"Would you like to approve this request?"
            ),
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Also notify the requester that their request is pending
        await context.bot.send_message(
            chat_id=requester_id,
            text=(
                f"🕒 *Join Request Sent*\n\n"
                f"Your request to join *{event_name}* has been sent to the organizer.\n"
                f"You'll be notified when they approve or decline your request."
            ),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error notifying organizer of request: {e}")

async def approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle approval-related callback queries.
    """
    query = update.callback_query
    
    if not query:
        return
        
    # Acknowledge the callback to stop the loading indicator
    await query.answer()
    
    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        logger.error("No user ID in approval callback")
        return
        
    callback_data = query.data
    if not callback_data:
        logger.error("No callback data in approval callback")
        return
        
    # Extract the action and parameters
    parts = callback_data.split('_')
    action = parts[0]
    
    if action == "approve" and len(parts) >= 3:
        event_id = parts[1]
        wallet_address = '_'.join(parts[2:])  # In case wallet contains underscores
        await handle_approval(query, user_id, event_id, wallet_address, approved=True)
    elif action == "decline" and len(parts) >= 3:
        event_id = parts[1]
        wallet_address = '_'.join(parts[2:])  # In case wallet contains underscores
        await handle_approval(query, user_id, event_id, wallet_address, approved=False)
    elif action == "requests" and len(parts) >= 2:
        event_id = parts[1]
        await handle_requests_list(query, user_id, event_id)
    else:
        logger.error(f"Unknown approval action: {action}")
        await query.edit_message_text(
            "❌ There was an error processing your request. Please try again."
        )

async def handle_approval(
    query,
    user_id: int,
    event_id: str,
    wallet_address: str,
    approved: bool
) -> None:
    """
    Handle the approval or decline of a join request.
    
    Args:
        query: The callback query
        user_id: The user ID of the organizer
        event_id: The event ID
        wallet_address: The wallet address of the requester
        approved: Whether the request was approved
    """
    # Get the context from the query
    context = query._context
    try:
        # Check if the user is the event organizer
        organizer_id = get_event_organizer_id(event_id)
        
        if organizer_id != user_id:
            await query.edit_message_text(
                "❌ You don't have permission to perform this action."
            )
            return
            
        # Get request info before processing
        requests = get_event_requests(event_id)
        request_info = requests.get(wallet_address)
        
        if not request_info:
            await query.edit_message_text(
                f"❌ Could not find request for wallet {wallet_address} in event {event_id}."
            )
            return
            
        requester_id = request_info.get("user_id")
        
        if approved:
            # Approve the request
            success = approve_join_request(event_id, wallet_address, user_id)
            
            if success:
                # Complete the join process
                
                # First, tell the user we're processing
                await query.answer("Processing on-chain transaction...")
                await query.edit_message_text(
                    f"⏳ Processing approval for {format_request_name(request_info)}...\n"
                    f"Sending transaction to Solana blockchain...",
                    parse_mode="Markdown"
                )
                
                # Try to join the event on-chain with timeout handling
                tx_signature = None
                tx_success = False
                try:
                    # Call blockchain function with timeout
                    tx_signature = await asyncio.wait_for(
                        join_event_onchain(wallet_address, event_id),
                        timeout=10.0  # 10-second timeout for blockchain operations
                    )
                    logger.info(f"On-chain join successful: {tx_signature}")
                    tx_success = True
                except asyncio.TimeoutError:
                    logger.error(f"On-chain join timed out for {wallet_address} on event {event_id}")
                except Exception as e:
                    logger.error(f"On-chain join failed: {e}")
                
                # Add the user to the event participants regardless of blockchain status
                requester_username = request_info.get("username")
                requester_first_name = request_info.get("first_name")
                requester_last_name = request_info.get("last_name")
                
                # Make sure requester_id is a valid integer
                requester_id_int = int(requester_id) if requester_id is not None else None
                
                if requester_id_int is None:
                    logger.error(f"Invalid requester ID for join request: {requester_id}")
                    await query.edit_message_text(
                        f"❌ Error processing approval: Invalid requester ID"
                    )
                    return
                
                add_success = add_event_participant(
                    event_id, wallet_address, requester_id_int, 
                    requester_username, requester_first_name, requester_last_name
                )
                
                if add_success:
                    # Get the current participant count
                    participant_count = count_event_participants(event_id)
                    
                    # Tell the organizer the request was approved with blockchain status
                    requester_name = format_request_name(request_info)
                    blockchain_status = "and recorded on-chain ⛓️" if tx_success else "locally only 📋"
                    
                    await query.edit_message_text(
                        f"✅ *Request Approved*\n\n"
                        f"You approved {requester_name}'s request to join event {event_id} {blockchain_status}.\n\n"
                        f"They are now participant #{participant_count}.",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("View All Requests", callback_data=f"requests_{event_id}")]
                        ])
                    )
                    
                    # Notify the requester that they've been approved
                    if requester_id:
                        # Generate QR code for the event
                        qr_image_path = generate_join_qr(event_id)
                        
                        # Send message to the requester
                        # Format messages with blockchain status
                        on_chain_status = "and recorded on the Solana blockchain ⛓️" if tx_success else "with a local record only 📋"
                        explorer_link = f"\n\n[View Transaction on Explorer](https://explorer.solana.com/tx/{tx_signature}?cluster=devnet)" if tx_success else ""
                        
                        await context.bot.send_message(
                            chat_id=requester_id,
                            text=(
                                f"🎉 *Join Request Approved*\n\n"
                                f"Your request to join event *{event_id}* has been approved {on_chain_status}!\n\n"
                                f"You are participant #{participant_count}{explorer_link}"
                            ),
                            parse_mode="Markdown",
                            disable_web_page_preview=True
                        )
                        
                        # Send the event QR code if available
                        if qr_image_path and os.path.exists(qr_image_path):
                            with open(qr_image_path, 'rb') as photo:
                                await context.bot.send_photo(
                                    chat_id=requester_id,
                                    photo=photo,
                                    caption=f"Here's your QR code for event {event_id}. Share this with others!"
                                )
                else:
                    await query.edit_message_text(
                        f"❌ There was an error adding {format_request_name(request_info)} to the event."
                    )
            else:
                await query.edit_message_text(
                    f"❌ There was an error approving {format_request_name(request_info)}'s request."
                )
        else:
            # Decline the request
            success = decline_join_request(event_id, wallet_address, user_id)
            
            if success:
                # Tell the organizer the request was declined
                await query.edit_message_text(
                    f"❌ You declined {format_request_name(request_info)}'s request to join event {event_id}.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("View All Requests", callback_data=f"requests_{event_id}")]
                    ])
                )
                
                # Notify the requester that they've been declined
                if requester_id:
                    await context.bot.send_message(
                        chat_id=requester_id,
                        text=f"❌ Your request to join event {event_id} was declined by the organizer."
                    )
            else:
                await query.edit_message_text(
                    f"❌ There was an error declining {format_request_name(request_info)}'s request."
                )
                
    except Exception as e:
        logger.error(f"Error handling approval: {e}")
        await query.edit_message_text(
            f"❌ An error occurred while processing the request: {str(e)}"
        )

async def handle_requests_list(
    query,
    user_id: int,
    event_id: str
) -> None:
    """
    Handle showing the list of join requests for an event.
    
    Args:
        query: The callback query
        user_id: The user ID of the requester
        event_id: The event ID
    """
    # Get the context from the query
    context = query._context
    try:
        # Check if the user is the event organizer
        organizer_id = get_event_organizer_id(event_id)
        
        if organizer_id != user_id:
            await query.edit_message_text(
                "❌ You don't have permission to view requests for this event."
            )
            return
            
        # Format the list of requests
        requests_text = format_requests_list(event_id)
        
        # Get the requests
        requests = get_event_requests(event_id)
        
        # Create buttons for each request
        buttons = []
        for wallet, request_info in requests.items():
            if request_info.get("status") == "pending":
                name = format_request_name(request_info)
                buttons.append([
                    InlineKeyboardButton(f"✅ {name}", callback_data=f"approve_{event_id}_{wallet}"),
                    InlineKeyboardButton(f"❌ {name}", callback_data=f"decline_{event_id}_{wallet}")
                ])
        
        # Add a back button
        buttons.append([InlineKeyboardButton("Back to Menu", callback_data="start")])
        
        # Show the requests
        await query.edit_message_text(
            f"👥 *Join Requests for Event {event_id}*\n\n{requests_text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
            
    except Exception as e:
        logger.error(f"Error handling requests list: {e}")
        await query.edit_message_text(
            f"❌ An error occurred while retrieving requests: {str(e)}"
        )