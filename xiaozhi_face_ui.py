import tkinter as tk
import os
import time
import threading
import json
import socket
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageTk

# Configuration
BG_WIDTH, BG_HEIGHT = 800, 480
IPC_HOST = "127.0.0.1"
CMD_PORT = 9999    # Send commands to bot
STATUS_PORT = 9998 # Listen for status from bot
VISION_TMP_PATH = "cache/vision_capture.jpg"


def send_ipc(message):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(message.encode(), (IPC_HOST, CMD_PORT))
        sock.close()
    except Exception: pass


class XiaozhiFaceUI:
    def __init__(self, master):
        self.master = master
        master.title("Xiaozhi Face UI")
        master.attributes('-fullscreen', True)
        master.configure(bg='black')
        
        # When closing UI, also stop the bot
        master.bind('<Escape>', self.quit_app)
        master.protocol("WM_DELETE_WINDOW", self.quit_app)

        master.bind('<Button-1>', self.on_tap)
        master.bind('<KeyPress-space>', self.on_space_press)
        master.bind('<KeyRelease-space>', self.on_space_release)
        master.bind('x', lambda e: send_ipc("abort"))
        master.bind('f', self.toggle_fullscreen)
        master.bind('c', lambda e: self.toggle_camera())

        self.current_state = "idle"
        self.animations = {}
        self.current_frame_index = 0
        self.space_held = False
        self.is_fullscreen = True
        
        # Camera Preview State
        self.camera_active = False
        self.camera_process = None
        self.next_photo_to_show = None
        self.photo_reference = None

        # Gallery State
        self.gallery_active = False
        self.gallery_image_path = None

        self.background_label = tk.Label(master, bg='black')
        self.background_label.place(x=0, y=0, width=BG_WIDTH, height=BG_HEIGHT)

        self.load_animations()
        self.update_animation()

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
                    except Exception: pass
            if not self.animations[state]:
                if state != "idle" and self.animations.get("idle"):
                    self.animations[state] = self.animations["idle"]
                else:
                    blank = Image.new('RGB', (BG_WIDTH, BG_HEIGHT), color='black')
                    self.animations[state].append(blank)

    def toggle_camera(self, force_state=None):
        if force_state is not None:
            self.camera_active = force_state
        else:
            self.camera_active = not self.camera_active
        
        if self.camera_active:
            self.gallery_active = False # Close gallery if camera opens
            print("Starting camera stream...", flush=True)
            cmd = [
                "rpicam-vid", "-t", "0", 
                "--width", "480", "--height", "360", 
                "--codec", "mjpeg", "--framerate", "12", 
                "--nopreview", "-o", "-"
            ]
            self.camera_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=0)
            threading.Thread(target=self.read_camera_stream, daemon=True).start()
        else:
            if self.camera_process:
                self.camera_process.terminate()
                self.camera_process = None
            self.next_photo_to_show = None
            self.photo_reference = None

    def read_camera_stream(self):
        byte_stream = b""
        while self.camera_active and self.camera_process:
            try:
                chunk = self.camera_process.stdout.read(8192)
                if not chunk: break
                byte_stream += chunk
                
                a = byte_stream.find(b'\xff\xd8')
                b = byte_stream.find(b'\xff\xd9')
                if a != -1 and b != -1 and b > a:
                    jpg = byte_stream[a:b+2]
                    byte_stream = byte_stream[b+2:]
                    
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame)
                        img = img.resize((BG_WIDTH, BG_HEIGHT), Image.Resampling.NEAREST)
                        # Store in temp variable, DO NOT create PhotoImage here (not thread-safe)
                        self.next_photo_to_show = img
            except Exception: break

    def capture_and_save(self):
        if self.camera_active:
            print("Capturing snap...", flush=True)
            cmd = ["rpicam-still", "-o", VISION_TMP_PATH, "--width", "1280", "--height", "960", "--immediate", "--nopreview"]
            subprocess.run(cmd)
            return True
        return False

    def update_animation(self):
        if self.gallery_active:
            # Just stay on the current image, check back later
            self.master.after(500, self.update_animation)
            return

        if self.camera_active:
            if self.next_photo_to_show:
                self.photo_reference = ImageTk.PhotoImage(image=self.next_photo_to_show)
                self.background_label.config(image=self.photo_reference)
                self.next_photo_to_show = None
            self.master.after(30, self.update_animation)
        else:
            frames = self.animations.get(self.current_state, [])
            if not frames: frames = self.animations.get("idle", [])
            if frames:
                self.current_frame_index = (self.current_frame_index + 1) % len(frames)
                self.photo_reference = ImageTk.PhotoImage(frames[self.current_frame_index])
                self.background_label.config(image=self.photo_reference)
            
            speed = 50 if self.current_state == "speaking" else 500
            self.master.after(speed, self.update_animation)

    def on_tap(self, event=None):
        if self.gallery_active:
            # Tap to exit gallery
            self.gallery_active = False
        elif self.camera_active:
            if self.capture_and_save():
                send_ipc("vision_ready")
        else:
            send_ipc("auto_toggle")

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

    def quit_app(self, event=None):
        print("Exiting and shutting down bot...", flush=True)
        send_ipc("shutdown")
        self.master.quit()

    def set_state(self, new_state):
        new_state = new_state.lower()
        if new_state in self.animations and self.current_state != new_state:
            self.current_state = new_state
            self.current_frame_index = 0

    def listen_for_status(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((IPC_HOST, STATUS_PORT))
        except Exception: return

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
                    elif cmd == "gallery_off": self.gallery_active = False
                    elif cmd == "show_image":
                        path = msg.get("path")
                        if path and os.path.exists(path):
                            self.display_custom_image(path)
            except Exception: pass

    def display_custom_image(self, path):
        """Display a specific image file on the screen."""
        try:
            with Image.open(path) as img:
                img = img.resize((BG_WIDTH, BG_HEIGHT), Image.Resampling.LANCZOS)
                self.photo_reference = ImageTk.PhotoImage(image=img)
                self.background_label.config(image=self.photo_reference)
                self.gallery_active = True
                self.gallery_image_path = path
        except Exception as e:
            print(f"Failed to display custom image: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    root.config(cursor="none")
    app = XiaozhiFaceUI(root)
    root.mainloop()
