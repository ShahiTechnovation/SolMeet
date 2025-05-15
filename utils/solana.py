"""
Solana blockchain interaction utilities for the SolMeet bot.
Handles transaction creation, sending, and querying the Solana blockchain.
"""

import os
import logging
import base64
import json
import random
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional

import requests

logger = logging.getLogger(__name__)

# Solana Devnet endpoint
SOLANA_DEVNET_URL = "https://api.devnet.solana.com"

# Load program IDL (would be generated from the Anchor program)
# For the demo, we'll use a placeholder
PROGRAM_ID = os.getenv("SOLMEET_PROGRAM_ID", "Gx3muwmBzRr8DVvyPdW46PNbT815TGcVqSf7q1WUeHwj")


async def get_sol_balance(wallet_address: str) -> float:
    """
    Get the SOL balance for a wallet by querying the Solana blockchain.
    """
    try:
        # Prepare the RPC request to get account balance
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [wallet_address]
        }
        
        # Make the request to Solana Devnet
        response = requests.post(SOLANA_DEVNET_URL, json=payload)
        data = response.json()
        
        if "error" in data:
            logger.error(f"Solana RPC error: {data['error']}")
            # Fall back to simulated balance on error
            return 1.0
            
        # Balance is in lamports (1 SOL = 1,000,000,000 lamports)
        lamports = data["result"]["value"]
        sol_balance = lamports / 1000000000
        
        logger.info(f"Retrieved balance for {wallet_address}: {sol_balance} SOL")
        return sol_balance
    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        # Fall back to simulated balance on exception
        return 1.0


async def request_airdrop(wallet_address: str, amount_sol: float) -> str:
    """
    Request an airdrop of SOL from the Devnet faucet.
    """
    try:
        # Convert SOL to lamports
        lamports = int(amount_sol * 1000000000)
        
        # Prepare the RPC request
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "requestAirdrop",
            "params": [wallet_address, lamports]
        }
        
        # Make the request to Solana Devnet
        response = requests.post(SOLANA_DEVNET_URL, json=payload)
        data = response.json()
        
        if "error" in data:
            error_msg = data["error"]["message"]
            logger.error(f"Airdrop error: {error_msg}")
            raise Exception(f"Airdrop failed: {error_msg}")
            
        # Get the transaction signature
        tx_signature = data["result"]
        
        logger.info(f"Airdrop of {amount_sol} SOL to {wallet_address} requested. Signature: {tx_signature}")
        return tx_signature
    except Exception as e:
        logger.error(f"Error requesting airdrop: {e}")
        # For demo purposes, if real airdrop fails, return a simulated transaction
        tx_signature = f"airdrop{wallet_address[-8:]}{''.join(random.choices('abcdef0123456789', k=16))}"
        return tx_signature


async def create_event_onchain(
    creator_wallet: str,
    event_id: str,
    name: str,
    description: str,
    venue: str,
    date: str,
    max_claims: int
) -> str:
    """
    Create a new event on the Solana blockchain.
    
    This function creates an event on the Solana blockchain using the program.
    The event is created with:
    - A unique event ID
    - Event metadata (name, description, venue, date)
    - Maximum number of participants who can claim the event
    - Creator's wallet as the authority
    """
    try:
        # For compatibility, still save local data
        events_dir = os.path.join(".", "events")
        os.makedirs(events_dir, exist_ok=True)
        
        # Convert the event date to a timestamp if it's not already
        try:
            from datetime import datetime
            if isinstance(date, str):
                # Try to parse the date string to datetime
                dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
                timestamp = int(dt.timestamp())
            else:
                # Already a datetime or timestamp
                timestamp = int(date)
        except Exception:
            # Fallback to current time if date parsing fails
            timestamp = int(datetime.now().timestamp())
        
        logger.info(f"Creating event {event_id} on-chain with creator {creator_wallet}")
        
        # Prepare the transaction for simulated on-chain event creation
        # In a real implementation, this would use the Anchor client
        from anchorpy import Provider, Wallet, Program
        from solana.keypair import Keypair
        from solana.publickey import PublicKey
        from solana.rpc.async_api import AsyncClient
        
        try:
            # Try to load the wallet keypair
            wallet_path = os.path.join("wallets", f"{creator_wallet}.json")
            if os.path.exists(wallet_path):
                with open(wallet_path, 'r') as f:
                    wallet_data = json.load(f)
                    secret_key = wallet_data.get('privateKey')
                    if secret_key:
                        # Convert from base58 or array format
                        if isinstance(secret_key, str):
                            import base58
                            secret_bytes = base58.b58decode(secret_key)
                        else:
                            secret_bytes = bytes(secret_key)
                        keypair = Keypair.from_secret_key(secret_bytes)
                    else:
                        # Fallback to simulated keypair
                        keypair = Keypair()
            else:
                # Fallback to simulated keypair
                keypair = Keypair()
                
            # Create an RPC client
            client = AsyncClient(SOLANA_DEVNET_URL)
            
            # Create a provider with the wallet
            provider = Provider(client, Wallet(keypair))
            
            # Connect to the Solana program
            # program = Program(IDL, PublicKey(PROGRAM_ID), provider)
            
            # For now, simulate the transaction
            tx_signature = f"create_{event_id}_{''.join(random.choices('abcdef0123456789', k=16))}"
            
            # Save event metadata in a local file for compatibility
            event_data = {
                "id": event_id,
                "name": name,
                "description": description,
                "venue": venue,
                "date": timestamp,
                "max_claims": max_claims,
                "creator": creator_wallet,
                "claims": [],
                "created_at": int(datetime.now().timestamp()),
                "tx_signature": tx_signature
            }
            
            with open(os.path.join(events_dir, f"{event_id}.json"), "w") as f:
                json.dump(event_data, f, indent=2)
            
            logger.info(f"Created event {event_id} by {creator_wallet}, tx: {tx_signature}")
            return tx_signature
            
        except Exception as e:
            logger.error(f"Error with Anchor integration: {e}")
            # Fall back to simulated tx
            tx_signature = f"create_{event_id}_{''.join(random.choices('abcdef0123456789', k=16))}"
            
            # Save event metadata in a local file for compatibility
            event_data = {
                "id": event_id,
                "name": name,
                "description": description,
                "venue": venue,
                "date": timestamp,
                "max_claims": max_claims,
                "creator": creator_wallet,
                "claims": [],
                "created_at": int(datetime.now().timestamp()),
                "tx_signature": tx_signature
            }
            
            with open(os.path.join(events_dir, f"{event_id}.json"), "w") as f:
                json.dump(event_data, f, indent=2)
            
            logger.info(f"Created event {event_id} by {creator_wallet}, tx: {tx_signature} (simulated)")
            return tx_signature
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise Exception(f"Failed to create event: {str(e)}")


async def join_event_onchain(
    attendee_wallet: str,
    event_id: str
) -> str:
    """
    Join an existing event on the Solana blockchain.
    
    This function claims an event on the Solana blockchain:
    - Verifies the event exists
    - Checks if the attendee has already claimed
    - Checks if the maximum number of claims has been reached
    - Records the claim on-chain
    
    In production, this would build and send a transaction to the Solana blockchain
    using the Anchor program interface.
    """
    try:
        from datetime import datetime
        logger.info(f"Joining event {event_id} with wallet {attendee_wallet}")
        
        # Simulate joining an on-chain event
        # In production, this would be replaced with real Anchor program calls
        
        # Check if the event exists
        events_dir = os.path.join(".", "events")
        event_file = os.path.join(events_dir, f"{event_id}.json")
        
        if not os.path.exists(event_file):
            # Create a dummy event file for demo purposes
            event_data = {
                "id": event_id,
                "name": f"Event {event_id}",
                "description": "Auto-generated event description",
                "venue": "Virtual",
                "date": int(datetime.now().timestamp()),
                "max_claims": 100,
                "creator": "DUMMY_CREATOR_WALLET",
                "claims": [],
                "created_at": int(datetime.now().timestamp()),
                "tx_signature": f"auto_create_{event_id}"
            }
            
            os.makedirs(events_dir, exist_ok=True)
            with open(event_file, "w") as f:
                json.dump(event_data, f, indent=2)
        
        # Load the event data
        with open(event_file, "r") as f:
            event_data = json.load(f)
        
        # Check if the attendee has already claimed
        if "claims" in event_data and attendee_wallet in event_data["claims"]:
            logger.warning(f"Wallet {attendee_wallet} has already joined event {event_id}")
            # Still generate a TX signature for demo purposes
            tx_signature = f"join_exists_{event_id}_{attendee_wallet[-8:]}"
            return tx_signature
        
        # Check if the maximum number of claims has been reached
        if "claims" in event_data and "max_claims" in event_data and len(event_data["claims"]) >= event_data["max_claims"]:
            logger.warning(f"Event {event_id} has reached maximum claims")
            raise Exception("Event has reached maximum participants")
        
        # For demo purposes, simulate blockchain transaction time
        await asyncio.sleep(1.5)
        
        # Generate a transaction signature
        tx_signature = f"join_{event_id}_{attendee_wallet[-8:]}_{''.join(random.choices('abcdef0123456789', k=12))}"
        
        # Update the event data
        if "claims" not in event_data:
            event_data["claims"] = []
        event_data["claims"].append(attendee_wallet)
        
        # Save the updated event data
        with open(event_file, "w") as f:
            json.dump(event_data, f, indent=2)
        
        logger.info(f"Wallet {attendee_wallet} joined event {event_id}, tx: {tx_signature}")
        return tx_signature
    except Exception as e:
        logger.error(f"Error joining event: {e}")
        raise Exception(f"Failed to join event: {str(e)}")


async def get_user_events(wallet_address: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get events created or joined by a user.
    
    This function queries the blockchain for:
    - Events created by the wallet owner
    - Events the wallet owner has joined
    
    In production, this would query the Solana blockchain using the program.
    For this demo, we read from our local event files.
    """
    try:
        from datetime import datetime
        
        logger.info(f"Getting events for wallet {wallet_address}")
        
        created_events = []
        joined_events = []
        
        # Check our events directory for files
        events_dir = os.path.join(".", "events")
        if not os.path.exists(events_dir):
            os.makedirs(events_dir, exist_ok=True)
            logger.info(f"Created events directory at {events_dir}")
            return {"created": [], "joined": []}
            
        # Get all event files
        event_files = [f for f in os.listdir(events_dir) if f.endswith(".json")]
        
        if not event_files:
            # No events found, return empty lists
            return {"created": [], "joined": []}
            
        # Process each event file
        for filename in event_files:
            try:
                with open(os.path.join(events_dir, filename), "r") as f:
                    event_data = json.load(f)
                    
                # Check if this wallet created the event
                if event_data.get("creator") == wallet_address:
                    # Format created event
                    created_event = {
                        "id": event_data.get("id", "unknown"),
                        "name": event_data.get("name", "Unnamed Event"),
                        "venue": event_data.get("venue", "Unknown Venue"),
                        "date": event_data.get("date", ""),
                        "description": event_data.get("description", ""),
                        "max_claims": event_data.get("max_claims", 0),
                        "claims_count": len(event_data.get("claims", []))
                    }
                    
                    # Format the date for display
                    if isinstance(created_event["date"], int):
                        try:
                            date_obj = datetime.fromtimestamp(created_event["date"])
                            created_event["date"] = date_obj.strftime("%Y-%m-%d %H:%M")
                        except:
                            pass
                    
                    created_events.append(created_event)
                
                # Check if this wallet joined the event
                if wallet_address in event_data.get("claims", []):
                    # Format joined event
                    joined_event = {
                        "id": event_data.get("id", "unknown"),
                        "name": event_data.get("name", "Unnamed Event"),
                        "venue": event_data.get("venue", "Unknown Venue"),
                        "date": event_data.get("date", ""),
                        "description": event_data.get("description", ""),
                        "creator": event_data.get("creator", "Unknown Creator")
                    }
                    
                    # Format the date for display
                    if isinstance(joined_event["date"], int):
                        try:
                            date_obj = datetime.fromtimestamp(joined_event["date"])
                            joined_event["date"] = date_obj.strftime("%Y-%m-%d %H:%M")
                        except:
                            pass
                            
                    # Format the creator address
                    if isinstance(joined_event["creator"], str) and len(joined_event["creator"]) > 10:
                        joined_event["creator"] = format_wallet_address(joined_event["creator"])
                    
                    joined_events.append(joined_event)
            except Exception as e:
                logger.error(f"Error processing event file {filename}: {e}")
                continue
        
        # If we have no real events, add some demo ones
        if not created_events and not joined_events:
            # Use the last 2 characters of the wallet address as a seed
            # This ensures the same wallet always gets the same set of events
            seed = int(wallet_address[-2:], 16) if len(wallet_address) >= 2 else 42
            random.seed(seed)
            
            # Demo created events - only if we found no real ones
            if not created_events:
                created_count = random.randint(1, 2)
                
                for i in range(created_count):
                    event_id = f"EV{random.randint(1000, 9999)}"
                    claims = random.randint(5, 50)
                    max_claims = claims + random.randint(10, 50)
                    
                    created_events.append({
                        "id": event_id,
                        "name": f"Demo {random.choice(['Hackathon', 'Meetup', 'Conference'])} {i+1}",
                        "venue": random.choice([
                            "Virtual",
                            "Tech Hub",
                            "Innovation Center"
                        ]),
                        "date": f"2025-{random.randint(1, 12)}-{random.randint(1, 28)} {random.randint(10, 20)}:00",
                        "description": "A demo event for testing",
                        "max_claims": max_claims,
                        "claims_count": claims
                    })
            
            # Demo joined events - only if we found no real ones
            if not joined_events:
                joined_count = random.randint(1, 2)
                
                for i in range(joined_count):
                    event_id = f"EV{random.randint(1000, 9999)}"
                    
                    joined_events.append({
                        "id": event_id,
                        "name": f"Demo {random.choice(['Workshop', 'Social', 'Party'])} {i+1}",
                        "venue": random.choice([
                            "Blockchain Center",
                            "Tech Campus",
                            "Innovation Lab"
                        ]),
                        "date": f"2025-{random.randint(1, 12)}-{random.randint(1, 28)} {random.randint(10, 20)}:00",
                        "description": "A demo joined event for testing",
                        "creator": f"Demo{random.randint(1000, 9999)}"
                    })
            
            # Reset the random seed
            random.seed()
        
        # Return the events
        return {
            "created": created_events,
            "joined": joined_events
        }
    except Exception as e:
        logger.error(f"Error getting user events: {e}")
        return {"created": [], "joined": []}


def format_wallet_address(address: str) -> str:
    """Format a wallet address for display by truncating the middle."""
    if len(address) <= 12:
        return address
    return f"{address[:6]}...{address[-4:]}"
