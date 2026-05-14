import subprocess
import os
import logging
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

PRINTER_NAME = "Brother_Printer"
VISION_TMP_PATH = "cache/vision_capture.jpg"

def print_photo(arguments: dict) -> str:
    """
    Print the last captured photo to the configured network printer.
    """
    # 1. Check if the photo exists
    if not os.path.exists(VISION_TMP_PATH):
        return '{"success": false, "message": "No photo found to print. Please take a photo first."}'

    try:
        logger.info(f"Sending {VISION_TMP_PATH} to printer {PRINTER_NAME}...")
        
        # 2. Run the lp command
        # We use -o fit-to-page to make sure it looks good
        cmd = ["lp", "-d", PRINTER_NAME, "-o", "fit-to-page", VISION_TMP_PATH]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            logger.info("Print job submitted successfully.")
            return '{"success": true, "message": "The photo is being printed now!"}'
        else:
            error_msg = result.stderr.strip()
            logger.error(f"Print failed: {error_msg}")
            return f'{{"success": false, "message": "Printer error: {error_msg}"}}'

    except Exception as e:
        logger.error(f"Exception during printing: {e}")
        return f'{{"success": false, "message": "Failed to print: {str(e)}"}}'
