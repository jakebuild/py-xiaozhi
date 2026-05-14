import subprocess
import os
import logging
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

PRINTER_NAME = "Brother_Printer"
VISION_TMP_PATH = "cache/vision_capture.jpg"

def print_photo(arguments: dict) -> str:
    """
    Print a photo to the configured network printer.
    """
    # Use provided path or default to the last captured photo
    photo_path = arguments.get("path") or VISION_TMP_PATH
    
    # 1. Check if the photo exists
    if not os.path.exists(photo_path):
        return f'{{"success": false, "message": "File not found: {photo_path}"}}'

    try:
        logger.info(f"Sending {photo_path} to printer {PRINTER_NAME}...")
        
        # 2. Run the lp command
        cmd = ["lp", "-d", PRINTER_NAME, "-o", "fit-to-page", photo_path]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            logger.info("Print job submitted successfully.")
            return f'{{"success": true, "message": "The file {os.path.basename(photo_path)} is being printed now!"}}'
        else:
            error_msg = result.stderr.strip()
            logger.error(f"Print failed: {error_msg}")
            return f'{{"success": false, "message": "Printer error: {error_msg}"}}'

    except Exception as e:
        logger.error(f"Exception during printing: {e}")
        return f'{{"success": false, "message": "Failed to print: {str(e)}"}}'
