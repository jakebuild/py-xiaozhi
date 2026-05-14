import os
import json
import socket
import logging
from src.utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)

IPC_HOST = "127.0.0.1"
UI_STATUS_PORT = 9998

# Global state to track current gallery session
class GalleryState:
    images = []
    current_index = -1
    base_dir = "/home/jake/photos" # Default path

state = GalleryState()

def gallery_control(arguments: dict) -> str:
    """
    Manage the image gallery: scan, filter, next, prev, and print.
    """
    action = arguments.get("action", "scan")
    directory = arguments.get("directory", state.base_dir)
    query = arguments.get("query", "").lower()

    if action == "scan":
        if not os.path.exists(directory):
            return f'{{"success": false, "message": "Directory not found: {directory}"}}'
        
        state.base_dir = directory
        # Find all images
        found = []
        for root, dirs, files in os.walk(directory):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    full_path = os.path.join(root, f)
                    # Filter by name or folder name
                    if not query or query in full_path.lower():
                        found.append(full_path)
        
        state.images = sorted(found)
        if not state.images:
            return '{"success": false, "message": "No images found matching your query."}'
        
        state.current_index = 0
        _send_to_ui(state.images[state.current_index])
        return f'{{"success": true, "message": "Found {len(state.images)} images. Showing the first one.", "current_image": "{state.images[0]}"}}'

    elif action == "next":
        if not state.images:
            return '{"success": false, "message": "Gallery is empty. Try scanning first."}'
        state.current_index = (state.current_index + 1) % len(state.images)
        _send_to_ui(state.images[state.current_index])
        return f'{{"success": true, "message": "Showing next image.", "path": "{state.images[state.current_index]}"}}'

    elif action == "prev":
        if not state.images:
            return '{"success": false, "message": "Gallery is empty."}'
        state.current_index = (state.current_index - 1) % len(state.images)
        _send_to_ui(state.images[state.current_index])
        return f'{{"success": true, "message": "Showing previous image.", "path": "{state.images[state.current_index]}"}}'

    elif action == "close":
        state.images = []
        state.current_index = -1
        _send_cmd_to_ui("gallery_off")
        return '{"success": true, "message": "Gallery closed."}'

    elif action == "print":
        if state.current_index < 0 or not state.images:
            return '{"success": false, "message": "No image selected to print."}'
        
        # Call the existing printer tool logic
        # For simplicity in this tool, we just return the path so the agent can call the printer tool
        return f'{{"success": true, "action": "print_request", "path": "{state.images[state.current_index]}", "message": "I am ready to print this image. Should I proceed?"}}'

    return '{"success": false, "message": "Unknown action."}'

def _send_to_ui(path):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        cmd = json.dumps({"type": "command", "command": "show_image", "path": path})
        sock.sendto(cmd.encode(), (IPC_HOST, UI_STATUS_PORT))
        sock.close()
    except Exception as e:
        logger.error(f"Failed to tell UI to show gallery image: {e}")

def _send_cmd_to_ui(command):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        cmd = json.dumps({"type": "command", "command": command})
        sock.sendto(cmd.encode(), (IPC_HOST, UI_STATUS_PORT))
        sock.close()
    except Exception: pass
