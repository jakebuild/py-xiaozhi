import requests
import os
import logging
import json
import socket
from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# IPC Configuration for communicating with Face UI
IPC_HOST = "127.0.0.1"
UI_STATUS_PORT = 9998
GEN_IMAGE_PATH = "cache/generated_image.jpg"

def generate_image(arguments: dict) -> str:
    """
    Generate an image based on a prompt and display it on the Face UI.
    """
    prompt = arguments.get("prompt", "")
    if not prompt:
        return '{"success": false, "message": "Please provide a prompt for the image."}'

    config = ConfigManager.get_instance()
    api_key = config.get_config("CAMERA.VLapi_key", "")
    # Note: Using the same ZhipuAI endpoint base if possible, or a specific one for CogView
    api_url = "https://open.bigmodel.cn/api/paas/v4/images/generations"

    if not api_key:
        return '{"success": false, "message": "API Key is not configured in config.json."}'

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "cogview-3", # ZhipuAI's generation model
        "prompt": prompt
    }

    try:
        logger.info(f"Generating image for prompt: {prompt}")
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        if response.status_code != 200:
            return f'{{"success": false, "message": "API Error: {response.text}"}}'

        data = response.json()
        image_url = data.get("data", [{}])[0].get("url")
        
        if not image_url:
            return '{"success": false, "message": "No image URL returned from API."}'

        # Download the image
        img_response = requests.get(image_url)
        if img_response.status_code == 200:
            os.makedirs(os.path.dirname(GEN_IMAGE_PATH), exist_ok=True)
            with open(GEN_IMAGE_PATH, "wb") as f:
                f.write(img_response.content)
            
            # Tell Face UI to show this image
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                cmd = json.dumps({"type": "command", "command": "show_image", "path": GEN_IMAGE_PATH})
                sock.sendto(cmd.encode(), (IPC_HOST, UI_STATUS_PORT))
                sock.close()
            except Exception as e:
                logger.error(f"Failed to tell UI to show image: {e}")

            return f'{{"success": true, "message": "I have generated the image and showing it on the screen now!", "image_path": "{GEN_IMAGE_PATH}"}}'
        else:
            return '{"success": false, "message": "Failed to download the generated image."}'

    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        return f'{{"success": false, "message": "Error: {str(e)}"}}'
