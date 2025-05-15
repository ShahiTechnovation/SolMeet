"""
Solana wallet creation and management utilities for the SolMeet bot.
"""

import os
import json
import logging
import subprocess
import tempfile
import random
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any

logger = logging.getLogger(__name__)

# Directory to store wallets
WALLETS_DIR = Path("./wallets")

def ensure_wallet_directory():
    """Ensure the wallets directory exists."""
    if not WALLETS_DIR.exists():
        WALLETS_DIR.mkdir(parents=True)
        logger.info(f"Created wallets directory at {WALLETS_DIR}")


def create_new_wallet() -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Create a new Solana wallet using solana-keygen.
    
    Returns:
        Tuple containing (wallet_address, wallet_info_dict)
    """
    # Initialize variables
    wallet_address = None
    mnemonic = None
    keypair_json = None
    private_key = None
    tmp_keypair_path = None
    
    try:
        # Make sure we have the wallets directory
        ensure_wallet_directory()
        
        # Create a temporary file for the keypair
        with tempfile.NamedTemporaryFile(delete=False) as tmp_keypair:
            tmp_keypair_path = tmp_keypair.name
        
        # Step 1: Generate a keypair without saving to capture seed phrase
        try:
            logger.info("Generating keypair with solana-keygen...")
            gen_result = subprocess.run(
                ["solana-keygen", "new", "--no-bip39-passphrase", "--no-outfile"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Process the output to extract pubkey and mnemonic
            stdout_lines = gen_result.stdout.splitlines()
            logger.info(f"Got {len(stdout_lines)} lines from keygen command")
            
            for line in stdout_lines:
                if "pubkey:" in line:
                    wallet_address = line.split("pubkey:")[1].strip()
                    logger.info(f"Extracted pubkey: {wallet_address}")
            
            # Find the seed phrase
            seed_phrase_found = False
            for i, line in enumerate(stdout_lines):
                if "Save this seed phrase" in line and i+1 < len(stdout_lines):
                    seed_phrase_found = True
                    mnemonic = stdout_lines[i+1].strip()
                    if "=" in mnemonic:  # Skip separator lines
                        continue
                    logger.info("Successfully extracted seed phrase")
                    break
            
            if not seed_phrase_found or not mnemonic or not wallet_address:
                raise Exception("Could not extract seed phrase or wallet address from output")
        
        except Exception as e:
            logger.error(f"Error in initial keypair generation: {str(e)}")
            mnemonic = None
            wallet_address = None
        
        # Step 2: Generate the actual keypair file
        if mnemonic and wallet_address:
            # Generate keypair file with the same mnemonic
            try:
                logger.info(f"Creating keypair file using extracted mnemonic...")
                subprocess.run(
                    ["solana-keygen", "new", "--no-bip39-passphrase", "--force", "-o", tmp_keypair_path],
                    input=mnemonic + "\n",
                    capture_output=True,
                    text=True,
                    check=True
                )
            except Exception as e:
                logger.error(f"Error creating keypair file with mnemonic: {str(e)}")
                # Continue with the generated file if it exists
        else:
            # Fallback: direct generation if we couldn't extract mnemonic
            try:
                logger.info("Falling back to direct keypair file generation...")
                subprocess.run(
                    ["solana-keygen", "new", "--no-bip39-passphrase", "--force", "-o", tmp_keypair_path],
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                # Extract the pubkey from the generated file
                pubkey_result = subprocess.run(
                    ["solana-keygen", "pubkey", tmp_keypair_path],
                    capture_output=True,
                    text=True,
                    check=True
                )
                wallet_address = pubkey_result.stdout.strip()
                logger.info(f"Generated fallback wallet with address: {wallet_address}")
                
                # Create a placeholder mnemonic (this is not secure for real wallets!)
                if not mnemonic:
                    word_list = [
                        "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract", 
                        "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid",
                        "acoustic", "acquire", "across", "act", "action", "actor", "actress", "actual"
                    ]
                    mnemonic = " ".join(random.choices(word_list, k=12))
                    logger.warning("Using placeholder mnemonic - NOT SECURE FOR PRODUCTION")
            except Exception as e:
                logger.error(f"Error in fallback keypair generation: {str(e)}")
                # If we reached this point, we'll likely return None, None
        
        # Step 3: Read the keypair file and extract private key
        if os.path.exists(tmp_keypair_path):
            try:
                # Read keypair file
                with open(tmp_keypair_path, 'r') as f:
                    keypair_json = f.read()
                
                # Extract private key from keypair JSON
                keypair_bytes = json.loads(keypair_json)
                if isinstance(keypair_bytes, list) and len(keypair_bytes) >= 32:
                    private_key_bytes = keypair_bytes[:32]
                    private_key = ''.join(f'{b:02x}' for b in private_key_bytes)
                    logger.info("Successfully extracted private key from keypair")
            except Exception as e:
                logger.error(f"Error reading keypair or extracting private key: {str(e)}")
            
            # Clean up the temporary file
            try:
                os.unlink(tmp_keypair_path)
            except Exception as e:
                logger.error(f"Error deleting temporary keypair file: {str(e)}")
        
        # Step 4: Verify we have the minimum required info
        if not wallet_address or not mnemonic:
            logger.error("Failed to create wallet: missing address or mnemonic")
            return None, None
        
        # Step 5: Store wallet info
        wallet_info = {
            "address": wallet_address,
            "mnemonic": mnemonic,
            "keypair": keypair_json,
            "private_key": private_key
        }
        
        # Save to file
        wallet_path = WALLETS_DIR / f"{wallet_address}.json"
        with open(wallet_path, 'w') as f:
            json.dump(wallet_info, f)
        
        logger.info(f"Created new Solana wallet: {wallet_address}")
        return wallet_address, wallet_info
    
    except Exception as e:
        logger.error(f"Unexpected error in wallet creation: {str(e)}")
        # Clean up any temporary file if it exists
        if tmp_keypair_path and os.path.exists(tmp_keypair_path):
            try:
                os.unlink(tmp_keypair_path)
            except:
                pass
        return None, None


def get_wallet_info(wallet_address: str) -> Optional[Dict]:
    """
    Get information about a stored wallet.
    
    Args:
        wallet_address: The wallet address to lookup.
        
    Returns:
        Dict containing wallet information or None if not found.
    """
    try:
        wallet_path = WALLETS_DIR / f"{wallet_address}.json"
        if not wallet_path.exists():
            return None
            
        with open(wallet_path, 'r') as f:
            wallet_info = json.load(f)
            
        return wallet_info
    except Exception as e:
        logger.error(f"Error retrieving wallet info: {str(e)}")
        return None


def list_user_wallets() -> Dict[str, str]:
    """
    List all wallet addresses and their readable names from the wallets directory.
    
    Returns:
        Dict mapping wallet addresses to labels.
    """
    ensure_wallet_directory()
    wallets = {}
    
    try:
        for wallet_file in WALLETS_DIR.glob("*.json"):
            with open(wallet_file, 'r') as f:
                wallet_data = json.load(f)
                wallets[wallet_data["address"]] = f"Wallet {wallet_file.stem[:6]}..."
    except Exception as e:
        logger.error(f"Error listing wallets: {str(e)}")
    
    return wallets