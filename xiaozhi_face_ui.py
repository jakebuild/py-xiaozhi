import tkinter as tk
import os
import time
import threading
import json
import socket
import cv2
from PIL import Image, ImageTk

# Configuration
BG_WIDTH, BG_HEIGHT = 800, 480
IPC_HOST = "127.0.0.1"
CMD_PORT = 9999    # Send commands to bot
STATUS_PORT = 9998 # Listen for status from bot
VISION_TMP_PATH = "cache/vision_capture.jpg"


def send_ipc(message):
    """Send a UDP message to the core engine."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message.encode(), (IPC_HOST, CMD_PORT))
        sock.close()
    except Exception as e:
        print(f"IPC send failed: {e}", flush=True)


class XiaozhiFaceUI:
    def __init__(self, master):
        self.master = master
        master.title("Xiaozhi Face UI")
        master.attributes('-fullscreen', True)
        master.configure(bg='black')
        master.bind('<Escape>', lambda e: master.quit())

        # Interaction bindings
        master.bind('<Button-1>', self.on_tap)
        master.bind('<KeyPress-space>', self.on_space_press)
        master.bind('<KeyRelease-space>', self.on_space_release)
        master.bind('x', lambda e: send_ipc("abort"))
        master.bind('f', self.toggle_fullscreen)
        # 'c' key to toggle camera preview manually
        master.bind('c', lambda e: self.toggle_camera())

        self.current_state = "idle"
        self.animations = {}
        self.current_frame_index = 0
        self.space_held = False
        self.is_fullscreen = True
        
        # Camera Preview State
        self.camera_active = False
        self.cap = None

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

    def toggle_camera(self, force_state=None):
        """Toggle the live camera preview on the Face UI."""
        if force_state is not None:
            self.camera_active = force_state
        else:
            self.camera_active = not self.camera_active
        
        if self.camera_active:
            print("Opening camera preview...", flush=True)
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        else:
            print("Closing camera preview.", flush=True)
            if self.cap:
                self.cap.release()
                self.cap = None

    def capture_and_save(self):
        """Snap a photo from the current preview and save it for the bot."""
        if not self.cap or not self.camera_active:
            # Temporarily open camera if not active
            temp_cap = cv2.VideoCapture(0)
            ret, frame = temp_cap.read()
            temp_cap.release()
        else:
            ret, frame = self.cap.read()
        
        if ret:
            os.makedirs(os.path.dirname(VISION_TMP_PATH), exist_ok=True)
            cv2.imwrite(VISION_TMP_PATH, frame)
            print(f"Photo captured and saved to {VISION_TMP_PATH}", flush=True)
            return True
        return False

    def update_animation(self):
        if self.camera_active and self.cap:
            # Show Camera Feed
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                img = img.resize((BG_WIDTH, BG_HEIGHT), Image.Resampling.LANCZOS)
                self.current_photo = ImageTk.PhotoImage(image=img)
                self.background_label.config(image=self.current_photo)
            self.master.after(50, self.update_animation) # High freq for camera
        else:
            # Show Animated Face
            frames = self.animations.get(self.current_state, [])
            if not frames: frames = self.animations.get("idle", [])
            if frames:
                self.current_frame_index = (self.current_frame_index + 1) % len(frames)
                self.current_photo = ImageTk.PhotoImage(frames[self.current_frame_index])
                self.background_label.config(image=self.current_photo)
            
            speed = 50 if self.current_state == "speaking" else 500
            self.master.after(speed, self.update_animation)

    def on_tap(self, event=None):
        if self.camera_active:
            # If camera is on, tap captures a photo!
            if self.capture_and_save():
                send_ipc("vision_ready") # Tell bot to process the saved photo
        else:
            print("Screen tapped! Sending auto_toggle...", flush=True)
            threading.Thread(target=send_ipc, args=("auto_toggle",), daemon=True).start()

    def on_space_press(self, event=None):
        if not self.space_held:
            self.space_held = True
            send_ipc("press")

    def on_space_release(self, event=None):
        if self.space_held:
            self.space_held = False
            send_ipc("release")

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.master.attributes("-fullscreen", self.is_fullscreen)

    def set_state(self, new_state):
        new_state = new_state.lower()
        if new_state in self.animations and self.current_state != new_state:
            print(f"UI State changed -> {new_state}", flush=True)
            self.current_state = new_state
            self.current_frame_index = 0

    def listen_for_status(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((IPC_HOST, STATUS_PORT))
            print(f"Face UI listening on port {STATUS_PORT}...", flush=True)
        except Exception as e:
            print(f"Failed to bind status port: {e}", flush=True)
            return

        while True:
            try:
                data, addr = sock.recvfrom(4096)
                msg = json.loads(data.decode())
                if msg.get("type") == "state_change":
                    new_state = msg.get("state", "").lower().split('.')[-1]
                    self.set_state(new_state)
                elif msg.get("type") == "command":
                    cmd = msg.get("command")
                    if cmd == "camera_on": self.toggle_camera(True)
                    elif cmd == "camera_off": self.toggle_camera(False)
                    elif cmd == "capture": self.capture_and_save()
            except Exception as e:
                print(f"UDP Receive Error: {e}", flush=True)


if __name__ == "__main__":
    root = tk.Tk()
    root.config(cursor="none")
    app = XiaozhiFaceUI(root)
    root.mainloop()
