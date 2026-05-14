import threading
import requests
import os
import time
import socket
import json
import base64

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# IPC Configuration for communicating with Face UI
IPC_HOST = "127.0.0.1"
UI_STATUS_PORT = 9998
VISION_TMP_PATH = "cache/vision_capture.jpg"


class Camera:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.jpeg_data = {"buf": b"", "len": 0}

        config = ConfigManager.get_instance()
        # We'll use a new config key for OpenAI to avoid confusion
        self.api_key = config.get_config("OPENAI.api_key", "")
        self.model = config.get_config("OPENAI.vision_model", "gpt-4o")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def capture(self) -> bool:
        """Capture a photo by requesting it from the Face UI via UDP."""
        try:
            logger.info("Requesting photo capture from Face UI...")
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            cmd = json.dumps({"type": "command", "command": "capture"})
            sock.sendto(cmd.encode(), (IPC_HOST, UI_STATUS_PORT))
            sock.close()

            start_time = time.time()
            while time.time() - start_time < 3:
                if os.path.exists(VISION_TMP_PATH):
                    if time.time() - os.path.getmtime(VISION_TMP_PATH) < 5:
                        with open(VISION_TMP_PATH, "rb") as f:
                            self.jpeg_data["buf"] = f.read()
                            self.jpeg_data["len"] = len(self.jpeg_data["buf"])
                        logger.info(f"Photo captured from UI (size: {self.jpeg_data['len']} bytes)")
                        return True
                time.sleep(0.2)

            logger.error("Face UI failed to provide a photo in time.")
            return False

        except Exception as e:
            logger.error(f"Exception during UI capture: {e}")
            return False

    def explain(self, question: str) -> str:
        """Send image to OpenAI GPT-4o for explanation."""
        if not self.api_key:
            return '{"success": false, "message": "OpenAI API Key not configured. Please add it to config.json."}'

        if not self.jpeg_data["buf"]:
            return '{"success": false, "message": "No photo data available"}'

        api_url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # Encode image to base64
        base64_image = base64.b64encode(self.jpeg_data["buf"]).decode('utf-8')

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": question or "Please describe this image in detail."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 500
        }

        try:
            logger.info(f"Sending photo to OpenAI ({self.model})...")
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code != 200:
                return f'{{"success": false, "message": "OpenAI Error {response.status_code}: {response.text}"}}'

            result = response.json()
            description = result['choices'][0]['message']['content']
            return description

        except Exception as e:
            return f'{{"success": false, "message": "Failed to call OpenAI: {str(e)}"}}'


def take_photo(arguments: dict) -> str:
    """Tool function called by the LLM."""
    camera = Camera.get_instance()
    question = arguments.get("question", "What is in this picture?")

    if not camera.capture():
        return '{"success": false, "message": "Could not access the camera preview. Make sure Face UI is running and camera is active."}'

    return camera.explain(question)
