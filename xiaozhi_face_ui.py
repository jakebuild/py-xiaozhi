import tkinter as tk
import os
import time
import threading
import json
import socket
from PIL import Image, ImageTk

# Configuration
BG_WIDTH, BG_HEIGHT = 800, 480
IPC_HOST = "127.0.0.1"
CMD_PORT = 9999    # Send commands to bot
STATUS_PORT = 9998 # Listen for status from bot


def send_ipc(message):
    """Send a UDP message to the core engine."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message.encode(), (IPC_HOST, CMD_PORT))
        sock.close()
        print(f"IPC sent: {message}", flush=True)
    except Exception as e:
        print(f"IPC send failed: {e}", flush=True)


class XiaozhiFaceUI:
    def __init__(self, master):
        self.master = master
        master.title("Xiaozhi Face UI")
        master.attributes('-fullscreen', True)
        master.configure(bg='black')
        master.bind('<Escape>', lambda e: master.quit())

        # Click/tap to talk (auto-conversation toggle)
        master.bind('<Button-1>', self.on_tap)
        # Spacebar: press = start listening, release = stop listening
        master.bind('<KeyPress-space>', self.on_space_press)
        master.bind('<KeyRelease-space>', self.on_space_release)
        # 'x' key to abort
        master.bind('x', lambda e: send_ipc(\"abort\"))
        # 'f' key to toggle fullscreen
        master.bind('f', self.toggle_fullscreen)

        self.is_fullscreen = True
        self.current_state = \"idle\"
        self.animations = {}
        self.current_frame_index = 0
        self.space_held = False

        self.background_label = tk.Label(master, bg='black')
        self.background_label.place(x=0, y=0, width=BG_WIDTH, height=BG_HEIGHT)

        self.load_animations()
        self.update_animation()

        # Start UDP status listener
        self.status_thread = threading.Thread(target=self.listen_for_status, daemon=True)
        self.status_thread.start()

    def load_animations(self):
        base_path = "faces"
        states = ["idle", "listening", "speaking", "thinking", "error"]

        for state in states:
            self.animations[state] = []
            folder = os.path.join(base_path, state)
            if os.path.exists(folder):
                files = sorted([f for f in os.listdir(folder) if f.lower().endswith('.png')])
                for f in files:
                    frame_path = os.path.join(folder, f)
                    try:
                        with Image.open(frame_path) as img:
                            img = img.resize((BG_WIDTH, BG_HEIGHT), Image.Resampling.LANCZOS)
                            self.animations[state].append(img.copy())
                    except Exception:
                        pass

            if not self.animations[state]:
                if state != "idle" and self.animations.get("idle"):
                    self.animations[state] = self.animations["idle"]
                else:
                    blank = Image.new('RGB', (BG_WIDTH, BG_HEIGHT), color='black')
                    self.animations[state].append(blank)

    def update_animation(self):
        frames = self.animations.get(self.current_state, [])
        if not frames:
            frames = self.animations.get("idle", [])

        if frames:
            self.current_frame_index = (self.current_frame_index + 1) % len(frames)
            self.current_photo = ImageTk.PhotoImage(frames[self.current_frame_index])
            self.background_label.config(image=self.current_photo)

        speed = 50 if self.current_state == "speaking" else 500
        self.master.after(speed, self.update_animation)

    def on_tap(self, event=None):
        """Tap/click toggles auto-conversation mode via UDP IPC."""
        print("Screen tapped! Sending auto_toggle...", flush=True)
        threading.Thread(target=send_ipc, args=("auto_toggle",), daemon=True).start()

    def on_space_press(self, event=None):
        """Hold space = push-to-talk start."""
        if not self.space_held:
            self.space_held = True
            print("Space pressed! Sending press...", flush=True)
            threading.Thread(target=send_ipc, args=("press",), daemon=True).start()

    def on_space_release(self, event=None):
        """Release space = push-to-talk stop."""
        if self.space_held:
            self.space_held = False
            print("Space released! Sending release...", flush=True)
            threading.Thread(target=send_ipc, args=("release",), daemon=True).start()

    def set_state(self, new_state):
        new_state = new_state.lower()
        if new_state in self.animations and self.current_state != new_state:
            print(f\"UI State changed -> {new_state}\", flush=True)
            self.current_state = new_state
            self.current_frame_index = 0

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.master.attributes(\"-fullscreen\", self.is_fullscreen)
        print(f\"Fullscreen toggled: {self.is_fullscreen}\", flush=True)

    def listen_for_status(self):
        """Listen for UDP status updates from the bot on port 9998."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((IPC_HOST, STATUS_PORT))
            print(f"Face UI listening for status on port {STATUS_PORT}...", flush=True)
        except Exception as e:
            print(f"Failed to bind status port: {e}", flush=True)
            return

        while True:
            try:
                data, addr = sock.recvfrom(4096)
                msg = json.loads(data.decode())
                if msg.get("type") == "state_change":
                    state_str = msg.get("state", "").lower()
                    # Map "DeviceState.IDLE" -> "idle"
                    new_state = state_str.split('.')[-1]
                    self.set_state(new_state)
                elif msg.get("type") == "event":
                    # Handle other events like STT/TTS if needed
                    pass
            except Exception as e:
                print(f"UDP Receive Error: {e}", flush=True)


if __name__ == "__main__":
    root = tk.Tk()
    root.config(cursor="none")
    app = XiaozhiFaceUI(root)
    root.mainloop()
