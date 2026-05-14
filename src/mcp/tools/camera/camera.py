import threading
import cv2
import requests
import os
import time
import socket
import json

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
        self.explain_url = ""
        self.explain_token = ""
        self.jpeg_data = {"buf": b"", "len": 0}

        config = ConfigManager.get_instance()
        # Use the ZhipuAI settings from config
        self.explain_url = config.get_config("CAMERA.Local_VL_url", "")
        self.explain_token = config.get_config("CAMERA.VLapi_key", "")
        self.model = config.get_config("CAMERA.models", "glm-4v-plus")

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
            
            # Send 'capture' command to Face UI via UDP port 9998
            # (Note: Face UI listens for commands on the status port in our implementation)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            cmd = json.dumps({"type": "command", "command": "capture"})
            sock.sendto(cmd.encode(), (IPC_HOST, UI_STATUS_PORT))
            sock.close()

            # Wait for the file to be saved by the UI (max 3 seconds)
            start_time = time.time()
            while time.time() - start_time < 3:
                if os.path.exists(VISION_TMP_PATH):
                    # Check if file is recently updated
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
        """Send image to Vision AI for explanation."""
        if not self.explain_url:
            return '{"success": false, "message": "Vision API URL not configured"}'

        if not self.jpeg_data["buf"]:
            return '{"success": false, "message": "No photo data available"}'

        # Prepare headers for ZhipuAI/BigModel or similar
        headers = {
            "Authorization": f"Bearer {self.explain_token}" if self.explain_token else ""
        }

        # Format for GLM-4V style API (Chat Completions with images)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question or "What is in this picture?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{self.encode_image_base64()}"
                            }
                        }
                    ]
                }
            ]
        }

        try:
            # Note: The original implementation used a simple POST with files.
            # Here I'm adapting to a more standard Vision LLM payload.
            # If the user's endpoint is a custom 'explain' service, we can revert.
            
            logger.info(f"Sending photo to vision service: {self.explain_url}")
            # For now, let's stick to the original multipart/form-data style if it was working
            files = {
                "question": (None, question),
                "file": ("camera.jpg", self.jpeg_data["buf"], "image/jpeg"),
            }
            response = requests.post(self.explain_url, headers=headers, files=files, timeout=30)

            if response.status_code != 200:
                return f'{{"success": false, "message": "API Error {response.status_code}: {response.text}"}}'

            return response.text

        except Exception as e:
            return f'{{"success": false, "message": "{str(e)}"}}'

    def encode_image_base64(self):
        import base64
        return base64.b64encode(self.jpeg_data["buf"]).decode('utf-8')


def take_photo(arguments: dict) -> str:
    """Tool function called by the LLM."""
    camera = Camera.get_instance()
    question = arguments.get("question", "Describe what you see in this photo.")

    # 1. Capture via UI
    if not camera.capture():
        return '{"success": false, "message": "Could not access the camera preview"}'

    # 2. Explain via AI
    return camera.explain(question)
