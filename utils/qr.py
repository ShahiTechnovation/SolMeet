"""
QR code generation utilities for the SolMeet bot.
"""

import base64
import logging
import os
import qrcode
from io import BytesIO
from typing import Optional, Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Directory to store generated QR codes
QR_DIR = Path("./qr_codes")

def ensure_qr_directory():
    """Ensure the QR codes directory exists."""
    if not QR_DIR.exists():
        QR_DIR.mkdir(parents=True)
        logger.info(f"Created QR codes directory at {QR_DIR}")


def generate_event_qr(event_id: str, event_name: str = None) -> str:
    """
    Generate a QR code for an event and save it to a file.
    
    Args:
        event_id: The ID of the event to encode in the QR code
        event_name: Optional name to display on the QR code
    
    Returns:
        The path to the saved QR code image
    """
    ensure_qr_directory()
    
    try:
        # Create a unique data string for the QR code that includes the event ID
        data = f"solmeet://join/{event_id}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create an image from the QR code
        img = qr.make_image(fill_color="black", back_color="white")
        
        # If event name is provided, add it to the image
        if event_name:
            # Convert to PIL Image if it's not already
            if not isinstance(img, Image.Image):
                img = img.get_image()
            
            # Create a new image with extra space for the text
            width, height = img.size
            new_img = Image.new('RGB', (width, height + 30), color='white')
            new_img.paste(img, (0, 0))
            
            # Add text
            draw = ImageDraw.Draw(new_img)
            
            # Try to use a nice font, or fall back to default
            try:
                # Try a common font path
                font_path = None
                for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 
                             "/usr/share/fonts/TTF/DejaVuSans.ttf"]:
                    if os.path.exists(path):
                        font_path = path
                        break
                
                if font_path:
                    font = ImageFont.truetype(font_path, 15)
                else:
                    font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()
            
            # Draw the text
            text_to_draw = event_name[:30] + "..." if len(event_name) > 30 else event_name
            w, h = draw.textsize(text_to_draw, font=font) if hasattr(draw, 'textsize') else (len(text_to_draw) * 7, 15)
            draw.text(((width - w) / 2, height + 10), text_to_draw, fill="black", font=font)
            
            img = new_img
        
        # Save to file
        filename = f"event_{event_id}.png"
        file_path = QR_DIR / filename
        img.save(file_path)
        
        logger.info(f"Generated QR code for event {event_id} at {file_path}")
        return str(file_path)
    except Exception as e:
        logger.error(f"Error generating event QR code: {e}")
        # Use external QR API as fallback
        return f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=event:{event_id}"


def generate_join_qr(event_id: str) -> str:
    """
    Generate a QR code specifically for joining an event.
    """
    return generate_event_qr(event_id)


def generate_wallet_qr(wallet_address: str) -> str:
    """
    Generate a QR code for a wallet address and save it to a file.
    
    Args:
        wallet_address: The wallet address to encode
    
    Returns:
        The path to the saved QR code image
    """
    ensure_qr_directory()
    
    try:
        # Format the data as a Solana address
        data = f"solana:{wallet_address}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create an image from the QR code
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to file
        filename = f"wallet_{wallet_address[:8]}.png"
        file_path = QR_DIR / filename
        img.save(file_path)
        
        logger.info(f"Generated QR code for wallet {wallet_address} at {file_path}")
        return str(file_path)
    except Exception as e:
        logger.error(f"Error generating wallet QR code: {e}")
        # Use external QR API as fallback
        return f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=solana:{wallet_address}"


def generate_qr_svg(data: str) -> Optional[str]:
    """
    Generate a QR code as an SVG string.
    
    This creates an SVG QR code that can be embedded directly in messages.
    
    Args:
        data: The data to encode in the QR code
        
    Returns:
        An SVG string representing the QR code, or None if generation failed
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create SVG XML
        svg_output = BytesIO()
        img = qr.make_image(fill_color="black", back_color="white", image_factory=qrcode.image.svg.SvgImage)
        img.save(svg_output)
        svg_data = svg_output.getvalue().decode('utf-8')
        
        return svg_data
    except Exception as e:
        logger.error(f"Error generating QR SVG: {e}")
        return None
        
        
def generate_qr_base64(data: str) -> Optional[str]:
    """
    Generate a QR code and return it as a base64-encoded PNG.
    
    Args:
        data: The data to encode in the QR code
        
    Returns:
        A base64-encoded PNG image, or None if generation failed
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create PNG
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return base64_image
    except Exception as e:
        logger.error(f"Error generating QR base64: {e}")
        return None
