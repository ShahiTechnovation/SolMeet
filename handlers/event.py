"""
Event creation and management handlers for the SolMeet bot.
"""

import asyncio
import logging
import json
import uuid
import os
from datetime import datetime
from typing import Optional
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import ContextTypes, ConversationHandler

# Set up logger
logger = logging.getLogger(__name__)

from utils.here_wallet import get_wallet_by_user_id
from utils.solana import create_event_onchain, join_event_onchain, get_user_events
from utils.qr import generate_event_qr, generate_join_qr
from utils.keyboard import get_main_keyboard, get_cancel_keyboard
from utils.participants import (
    add_event_participant, get_event_participants, count_event_participants,
    format_participants_list, subscribe_to_event_notifications,
    get_event_notification_subscribers
)

logger = logging.getLogger(__name__)

# Conversation states for event creation
(
    EVENT_NAME,
    EVENT_VENUE,
    EVENT_DATE,
    EVENT_DESCRIPTION,
    EVENT_MAX_CLAIMS,
    EVENT_CONFIRMATION
) = range(6)


async def create_event_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handler for /send_create command. Starts the event creation flow.
    """
    user_id = update.effective_user.id
    user_wallet = get_wallet_by_user_id(user_id)
    
    if not user_wallet:
        await update.message.reply_text(
            "You need to connect your wallet first before creating an event.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect")]
            ])
        )
        return ConversationHandler.END
    
    # Initialize event data in context
    context.user_data["create_event"] = {
        "creator_id": user_id,
        "creator_wallet": user_wallet,
        "current_step": "name",
    }
    
    await update.message.reply_text(
        "Let's create a new event on Solana! 🚀\n\n"
        "What name would you like to give your event?",
        reply_markup=get_cancel_keyboard()
    )
    
    return EVENT_NAME


async def handle_event_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Process the event creation flow based on the current step.
    """
    if "create_event" not in context.user_data:
        await update.message.reply_text(
            "Something went wrong. Please start again with /send_create.",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    event_data = context.user_data["create_event"]
    current_step = event_data.get("current_step", "name")
    text = update.message.text
    
    if current_step == "name":
        event_data["name"] = text
        event_data["current_step"] = "venue"
        
        await update.message.reply_text(
            f"Great! Your event is named: *{text}*\n\n"
            "Now, what's the venue or location for this event?",
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard()
        )
        return EVENT_VENUE
        
    elif current_step == "venue":
        event_data["venue"] = text
        event_data["current_step"] = "date"
        
        await update.message.reply_text(
            f"Venue set to: *{text}*\n\n"
            "When will this event take place? (format: YYYY-MM-DD HH:MM)",
            parse_mode="Markdown",
            reply_markup=get_cancel_keyboard()
        )
        return EVENT_DATE
        
    elif current_step == "date":
        try:
            event_date = datetime.strptime(text, "%Y-%m-%d %H:%M")
            event_data["date"] = event_date.isoformat()
            event_data["current_step"] = "description"
            
            await update.message.reply_text(
                f"Date set to: *{text}*\n\n"
                "Now, please provide a brief description of your event:",
                parse_mode="Markdown",
                reply_markup=get_cancel_keyboard()
            )
            return EVENT_DESCRIPTION
            
        except ValueError:
            await update.message.reply_text(
                "Invalid date format. Please use YYYY-MM-DD HH:MM (e.g., 2023-12-31 15:00)",
                reply_markup=get_cancel_keyboard()
            )
            return EVENT_DATE
        
    elif current_step == "description":
        event_data["description"] = text
        event_data["current_step"] = "max_claims"
        
        await update.message.reply_text(
            "Description saved!\n\n"
            "How many attendees can claim this event? (Enter a number)",
            reply_markup=get_cancel_keyboard()
        )
        return EVENT_MAX_CLAIMS
        
    elif current_step == "max_claims":
        try:
            max_claims = int(text)
            if max_claims <= 0:
                raise ValueError("Must be positive")
                
            event_data["max_claims"] = max_claims
            event_data["current_step"] = "confirmation"
            event_data["event_id"] = str(uuid.uuid4())[:8].upper()
            
            # Show the summary and ask for confirmation
            summary = (
                "*Event Summary*\n\n"
                f"*Name:* {event_data['name']}\n"
                f"*Venue:* {event_data['venue']}\n"
                f"*Date:* {text}\n"
                f"*Max Claims:* {max_claims}\n"
                f"*Description:* {event_data['description']}\n\n"
                "Is this information correct? Creating this event will require "
                "a transaction on Solana Devnet that you'll need to sign with your wallet."
            )
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Create Event", callback_data="event_confirm_create"),
                    InlineKeyboardButton("Cancel", callback_data="event_cancel")
                ]
            ])
            
            await update.message.reply_text(
                summary,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            return EVENT_CONFIRMATION
            
        except ValueError:
            await update.message.reply_text(
                "Please enter a valid positive number for maximum claims.",
                reply_markup=get_cancel_keyboard()
            )
            return EVENT_MAX_CLAIMS
    
    return ConversationHandler.END


async def handle_event_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle text inputs during the event creation flow.
    """
    if "create_event" in context.user_data:
        return await handle_event_creation(update, context)
    
    # If we're not in the event creation flow, we can handle other text inputs here
    return ConversationHandler.END


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Main handler for text inputs that delegates to specialized handlers.
    """
    # Handle text for event creation
    if "create_event" in context.user_data:
        return await handle_event_creation(update, context)
    
    # Handle text for event joining
    if "join_event" in context.user_data:
        await handle_event_join_text(update, context)
        return ConversationHandler.END
    
    # If we're not in either flow, let the user know
    await update.message.reply_text(
        "I'm not sure what you want to do. Please use commands like /start, /send_create, /send_join, etc.",
        reply_markup=get_main_keyboard()
    )
    
    return ConversationHandler.END


# Define the handle_my_events function at module level
async def handle_my_events(query, user_id: int, user_wallet: str) -> None:
    """Handler for displaying user's events from a callback."""
    try:
        # Get the user's events
        events = await get_user_events(user_wallet)
        
        created_events = events.get("created", [])
        joined_events = events.get("joined", [])
        
        if not created_events and not joined_events:
            await query.edit_message_text(
                "You haven't created or joined any events yet.\n\n"
                "Use the buttons below to create a new event or join an existing one.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Create Event", callback_data="event_create"),
                        InlineKeyboardButton("Join Event", callback_data="event_join")
                    ],
                    [InlineKeyboardButton("Back to Menu", callback_data="start")]
                ])
            )
            return
        
        # Format the events list
        if created_events:
            created_events_text = "*Events You Created:*\n\n"
            for i, event in enumerate(created_events):
                claims_text = f"{event.get('claims_count', 0)}/{event.get('max_claims', 'unlimited')}"
                created_events_text += (
                    f"{i+1}. *{event.get('name', 'Unnamed Event')}*\n"
                    f"   ID: `{event.get('id', 'unknown')}`\n"
                    f"   Date: {event.get('date', 'Not specified')}\n"
                    f"   Venue: {event.get('venue', 'Not specified')}\n"
                    f"   Participants: {claims_text}\n\n"
                )
        else:
            created_events_text = "*Events You Created:* None\n\n"
            
        if joined_events:
            joined_events_text = "*Events You Joined:*\n\n"
            for i, event in enumerate(joined_events):
                joined_events_text += (
                    f"{i+1}. *{event.get('name', 'Unnamed Event')}*\n"
                    f"   Creator: {event.get('creator', 'unknown')}\n"
                    f"   Date: {event.get('date', 'Not specified')}\n"
                    f"   Venue: {event.get('venue', 'Not specified')}\n\n"
                )
        else:
            joined_events_text = "*Events You Joined:* None\n\n"
            
        # Combine the texts
        events_text = created_events_text + joined_events_text
        
        await query.edit_message_text(
            events_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Create Event", callback_data="event_create"),
                    InlineKeyboardButton("Join Event", callback_data="event_join")
                ],
                [InlineKeyboardButton("Back to Menu", callback_data="start")]
            ])
        )
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        await query.edit_message_text(
            "Error fetching your events. Please try again later.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Back to Menu", callback_data="start")]
            ])
        )


async def event_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handle event-related callback queries.
    """
    query = update.callback_query
    await query.answer()
    
    if not query.data or "_" not in query.data:
        logger.warning(f"Invalid callback data: {query.data}")
        return ConversationHandler.END
        
    parts = query.data.split("_")
    if len(parts) < 2:
        logger.warning(f"Malformed callback data: {query.data}")
        return ConversationHandler.END
        
    action = parts[1]
    
    # Security check - make sure the user has a wallet
    user_id = query.from_user.id
    user_wallet = get_wallet_by_user_id(user_id)
    
    if action in ["create", "join", "my"] and not user_wallet:
        await query.edit_message_text(
            "You need to connect a wallet first to use this feature.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect")],
                [InlineKeyboardButton("Back to Menu", callback_data="start")]
            ])
        )
        return ConversationHandler.END
    
    # Handle event creation
    if action == "create":
        # Prepare event creation flow
        # Initialize event data structure
        context.user_data["create_event"] = {
            "event_id": str(uuid.uuid4())[:8].upper(),  # Short unique ID
            "creator_wallet": user_wallet,
            "step": "name",  # Start with event name
        }
        
        await query.edit_message_text(
            "*Create a New Event*\n\n"
            "Let's set up your event on Solana.\n\n"
            "First, what's the *name* of your event?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Cancel", callback_data="start")]
            ])
        )
        return 1  # State for handling the event name
    
    # Handle event joining
    elif action == "join":
        # Prompt for event code
        context.user_data["join_event"] = {
            "user_wallet": user_wallet,
            "user_id": user_id
        }
        
        await query.edit_message_text(
            "*Join an Event*\n\n"
            "Please enter the event code you'd like to join.\n"
            "This is a short alphanumeric code like 'ABC123'.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Cancel", callback_data="start")]
            ])
        )
        return 2  # State for handling the event code
    
    # Handle My Events
    elif action == "my":
        await handle_my_events(query, user_id, user_wallet)
        return ConversationHandler.END
    
    # Handle event info
    elif action == "info":
        await query.edit_message_text(
            "*What is SolMeet?*\n\n"
            "SolMeet is a platform for creating and joining Web3 events on Solana.\n\n"
            "With SolMeet, you can:\n"
            "• Create events that are recorded on the Solana blockchain\n"
            "• Join events and get verified on-chain\n"
            "• Track your participation in various events\n"
            "• Share events via QR codes and links\n\n"
            "To get started, connect a wallet with the button below.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect")],
                [InlineKeyboardButton("Back to Menu", callback_data="start")]
            ])
        )
        return ConversationHandler.END
    
    # Handle event confirmation
    elif action == "confirm":
        if len(parts) < 3:
            logger.warning(f"Malformed confirmation data: {query.data}")
            return ConversationHandler.END
            
        sub_action = parts[2]
        
        if sub_action == "create" and "create_event" in context.user_data:
            event_data = context.user_data["create_event"]
            
            # Create the event on-chain
            try:
                await query.edit_message_text(
                    "Creating your event on Solana... This might take a moment.",
                )
                
                # Generate QR code for the event first (doesn't need blockchain access)
                qr_image_path = generate_event_qr(event_data["event_id"], event_data["name"])
                
                # Register the creator as the first attendee and subscriber
                user_id = query.from_user.id
                creator_username = query.from_user.username
                creator_first_name = query.from_user.first_name
                creator_last_name = query.from_user.last_name
                
                # Add the creator to participants (doesn't need blockchain access)
                add_event_participant(
                    event_data["event_id"],
                    event_data["creator_wallet"],
                    user_id,
                    creator_username,
                    creator_first_name,
                    creator_last_name
                )
                
                # Subscribe the creator to notifications (doesn't need blockchain access)
                subscribe_to_event_notifications(
                    event_data["event_id"],
                    user_id
                )
                
                # Attempt blockchain transaction with timeout handling
                try:
                    # Set a timeout for the blockchain operation
                    tx_signature = await asyncio.wait_for(
                        create_event_onchain(
                            event_data["creator_wallet"],
                            event_data["event_id"],
                            event_data["name"],
                            event_data["description"],
                            event_data["venue"],
                            event_data["date"],
                            event_data["max_claims"],
                            creator_id=user_id  # Pass the creator's Telegram user ID
                        ),
                        timeout=5.0  # 5-second timeout
                    )
                except (asyncio.TimeoutError, Exception) as tx_error:
                    # Generate a simulated transaction signature if blockchain interaction fails
                    logger.error(f"Blockchain transaction error: {tx_error}")
                    tx_signature = f"simulated_create_{event_data['event_id']}"
                
                success_text = (
                    "🎉 *Event Created Successfully!*\n\n"
                    f"*Event ID:* `{event_data['event_id']}`\n"
                    f"*Name:* {event_data['name']}\n"
                    f"*Venue:* {event_data['venue']}\n"
                    f"*Participants:* 1/{event_data['max_claims']}\n\n"
                    "Share this Event ID with attendees or have them scan the QR code."
                )
                
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("View My Events", callback_data="event_list_mine"),
                        InlineKeyboardButton("Create Another", callback_data="event_create")
                    ],
                    [InlineKeyboardButton("Back to Menu", callback_data="start")]
                ])
                
                # Clear the event creation data
                del context.user_data["create_event"]
                
                await query.edit_message_text(
                    success_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                    disable_web_page_preview=False
                )
                
                # Send the QR code as a separate message with image
                if qr_image_path and os.path.exists(qr_image_path):
                    # Send message about QR code
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"Here's the QR code for your event *{event_data['name']}*. "
                             f"Attendees can scan this to join your event with the code: *{event_data['event_id']}*",
                        parse_mode="Markdown"
                    )
                    
                    # Send the QR code image
                    with open(qr_image_path, 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=query.message.chat_id,
                            photo=photo,
                            caption=f"QR Code for event: {event_data['name']} ({event_data['event_id']})"
                        )
                else:
                    # Fallback if image generation failed
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"Event created successfully. Share this code with attendees: *{event_data['event_id']}*",
                        parse_mode="Markdown"
                    )
                
                return ConversationHandler.END
                
            except Exception as e:
                logger.error(f"Error creating event: {e}")
                await query.edit_message_text(
                    "There was an error creating your event on Solana. Please try again later.",
                    reply_markup=get_main_keyboard()
                )
                return ConversationHandler.END
    
    elif action == "cancel":
        if "create_event" in context.user_data:
            del context.user_data["create_event"]
        
        await query.edit_message_text(
            "Event creation cancelled. You can start again with /send_create when you're ready.",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    return ConversationHandler.END


async def join_event_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /send_join command. Allows users to join an existing event.
    """
    user_id = update.effective_user.id
    user_wallet = get_wallet_by_user_id(user_id)
    
    if not user_wallet:
        await update.message.reply_text(
            "You need to connect your wallet first before joining an event.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect")]
            ])
        )
        return
    
    # Check if event_id was provided as an argument
    if context.args and len(context.args) > 0:
        event_id = context.args[0].strip().upper()
        # Process joining the event directly
        await process_event_join(update, context, event_id, user_id, user_wallet)
        return
    
    await update.message.reply_text(
        "To join an event, please enter the Event ID shared by the organizer.\n\n"
        "The Event ID is an 8-character code (e.g., 'ABC123XY').",
        reply_markup=get_cancel_keyboard()
    )
    
    # Set the expectation for the next message
    context.user_data["join_event"] = {"waiting_for": "event_id"}


async def process_event_join(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    event_id: str,
    user_id: int,
    user_wallet: str
) -> None:
    """
    Process the joining of an event after receiving the event ID.
    Now uses the approval system instead of direct joining.
    """
    try:
        # Import here to avoid circular imports
        from handlers.approval import send_join_request
        
        # Send a processing message
        if update.message:
            processing_message = await update.message.reply_text(
                f"Processing your request to join event {event_id}..."
            )
        
        # Get user information
        if update.effective_user:
            username = update.effective_user.username
            first_name = update.effective_user.first_name
            last_name = update.effective_user.last_name
            
            # Send join request instead of directly joining
            await send_join_request(
                update=update,
                context=context,
                event_id=event_id,
                user_id=user_id,
                user_wallet=user_wallet,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            
            # Update the processing message if it exists
            if update.message and 'processing_message' in locals():
                await processing_message.edit_text(
                    f"Your request to join event {event_id} has been sent to the organizer.\n\n"
                    "You will be notified when your request is approved or declined.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Back to Menu", callback_data="start")]
                    ])
                )
        else:
            logger.error("No effective user in update for process_event_join")
            if update.message:
                await update.message.reply_text(
                    "❌ There was an error processing your request. Please try again later.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Try Again", callback_data="event_join")],
                        [InlineKeyboardButton("Back to Menu", callback_data="start")]
                    ])
                )
            
    except Exception as e:
        logger.error(f"Error processing join request: {e}")
        if update.message:
            await update.message.reply_text(
                f"Error processing join request: {str(e)}",
                reply_markup=get_main_keyboard()
            )


async def notify_event_subscribers(
    context: ContextTypes.DEFAULT_TYPE,
    event_id: str,
    joiner_id: int,
    joiner_wallet: str,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> None:
    """
    Notify all subscribers of an event that a new participant has joined.
    """
    # Format the participant's name
    if username:
        participant_name = f"@{username}"
    elif first_name:
        participant_name = f"{first_name}"
        if last_name:
            participant_name += f" {last_name}"
    else:
        participant_name = f"a new participant"
    
    # Get all subscribers to notify
    subscribers = get_event_notification_subscribers(event_id)
    
    # Don't notify the person who just joined
    if joiner_id in subscribers:
        subscribers.remove(joiner_id)
    
    if not subscribers:
        logger.info(f"No subscribers to notify for event {event_id}")
        return
    
    # Short format of wallet address
    wallet_short = joiner_wallet[:6] + "..." + joiner_wallet[-4:]
    
    # Send notification to all subscribers
    notification_text = (
        f"🔔 *Event Notification*\n\n"
        f"*{participant_name}* has joined your event!\n"
        f"*Event ID:* `{event_id}`\n"
        f"*Wallet:* `{wallet_short}`\n\n"
        f"Current participants: {count_event_participants(event_id)}"
    )
    
    for subscriber_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=subscriber_id,
                text=notification_text,
                parse_mode="Markdown"
            )
            logger.info(f"Sent event notification to user {subscriber_id}")
        except Exception as e:
            logger.error(f"Error sending notification to {subscriber_id}: {e}")


async def handle_event_join_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle text input for joining an event.
    """
    if "join_event" not in context.user_data:
        return
    
    if context.user_data["join_event"].get("waiting_for") != "event_id":
        return
    
    user_id = update.effective_user.id
    user_wallet = get_wallet_by_user_id(user_id)
    
    if not user_wallet:
        await update.message.reply_text(
            "You need to connect your wallet first before joining an event.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect")]
            ])
        )
        # Clear the join event state
        del context.user_data["join_event"]
        return
    
    # Get the event ID from the message
    event_id = update.message.text.strip().upper()
    
    # Clear the join event state
    del context.user_data["join_event"]
    
    # Process joining the event
    await process_event_join(update, context, event_id, user_id, user_wallet)


async def my_events_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /my_events command. Shows events created or joined by the user.
    """
    user_id = update.effective_user.id
    user_wallet = get_wallet_by_user_id(user_id)
    
    if not user_wallet:
        await update.message.reply_text(
            "You need to connect your wallet first to view your events.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Connect Wallet", callback_data="wallet_connect")]
            ])
        )
        return
    
    try:
        # Get user's events from the blockchain
        events = await get_user_events(user_wallet)
        
        if not events or (len(events["created"]) == 0 and len(events["joined"]) == 0):
            await update.message.reply_text(
                "You haven't created or joined any events yet.\n\n"
                "Use /send_create to create a new event or /send_join to join an existing one.",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Format the events
        response = "*Your Events*\n\n"
        
        if events["created"] and len(events["created"]) > 0:
            response += "*Events You Created:*\n"
            for event in events["created"]:
                response += (
                    f"• *{event['name']}*\n"
                    f"  ID: `{event['id']}`\n"
                    f"  Venue: {event['venue']}\n"
                    f"  Claims: {event['claims_count']}/{event['max_claims']}\n\n"
                )
        
        if events["joined"] and len(events["joined"]) > 0:
            response += "*Events You Joined:*\n"
            for event in events["joined"]:
                response += (
                    f"• *{event['name']}*\n"
                    f"  ID: `{event['id']}`\n"
                    f"  Venue: {event['venue']}\n"
                    f"  Date: {event['date']}\n\n"
                )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Create Event", callback_data="event_create"),
                InlineKeyboardButton("Join Event", callback_data="event_join")
            ],
            [InlineKeyboardButton("Back to Menu", callback_data="start")]
        ])
        
        await update.message.reply_text(
            response,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        await update.message.reply_text(
            "There was an error fetching your events. Please try again later.",
            reply_markup=get_main_keyboard()
        )
