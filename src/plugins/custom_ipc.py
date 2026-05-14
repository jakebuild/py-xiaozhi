import asyncio
import json
import logging
from src.core.plugin_manager import BasePlugin
from src.constants.constants import DeviceState

logger = logging.getLogger(__name__)

class CustomIPCPlugin(BasePlugin):
    name = 'custom_ipc'
    description = 'UDP IPC for external control and status broadcasting'
    priority = 80  # After UI and shortcuts
    
    def __init__(self):
        super().__init__()
        self.app = None
        self.transport = None
        self.broadcast_addr = ('127.0.0.1', 9998) # Target for face UI
        
    class UDPProtocol(asyncio.DatagramProtocol):
        def __init__(self, plugin):
            self.plugin = plugin
            self.app = plugin.app
            
        def datagram_received(self, data, addr):
            try:
                message = data.decode().strip()
                logger.info(f'IPC received: {message} from {addr}')
                
                # Handle simple string commands for backward compatibility
                if message == 'press':
                    asyncio.create_task(self.app.start_listening_manual())
                elif message == 'release':
                    asyncio.create_task(self.app.stop_listening_manual())
                elif message == 'abort' or message == 'stop':
                    from src.constants.constants import AbortReason
                    asyncio.create_task(self.app.abort_speaking(AbortReason.USER_INTERRUPTION))
                elif message == 'auto_toggle':
                    asyncio.create_task(self.app.start_auto_conversation())
                elif message == 'ping':
                    self.plugin.broadcast_state(self.app.device_state)
                
                # Future: Handle JSON commands
                try:
                    cmd_data = json.loads(message)
                    self.handle_json_command(cmd_data)
                except json.JSONDecodeError:
                    pass
            except Exception as e:
                logger.error(f"Error processing IPC message: {e}")

        def handle_json_command(self, data):
            cmd = data.get("command")
            if cmd == "set_volume":
                # Example: {"command": "set_volume", "value": 70}
                pass # Implementation depends on how volume is managed

    def broadcast_state(self, state):
        """Send state to Face UI via UDP."""
        if not self.transport:
            return
        try:
            msg = json.dumps({"type": "state_change", "state": str(state)})
            self.transport.sendto(msg.encode(), self.broadcast_addr)
        except Exception as e:
            logger.debug(f"Failed to broadcast state: {e}")

    async def on_device_state_changed(self, state: DeviceState):
        self.broadcast_state(state)

    async def on_incoming_json(self, message):
        """Relay interesting JSON messages to Face UI."""
        if not self.transport:
            return
        msg_type = message.get("type")
        if msg_type in ["stt", "tts", "llm"]:
            try:
                payload = json.dumps({
                    "type": "event",
                    "event_type": msg_type,
                    "data": message
                })
                self.transport.sendto(payload.encode(), self.broadcast_addr)
            except Exception:
                pass

    async def setup(self, app):
        self.app = app
        
    async def start(self):
        loop = asyncio.get_running_loop()
        try:
            self.transport, _ = await loop.create_datagram_endpoint(
                lambda: self.UDPProtocol(self),
                local_addr=('127.0.0.1', 9999)
            )
            logger.info('Custom IPC plugin started on UDP 9999')
            # Broadcast initial state
            self.broadcast_state(self.app.device_state)
            return True
        except Exception as e:
            logger.error(f'Failed to start IPC plugin: {e}')
            return False
            
    async def stop(self):
        if self.transport:
            self.transport.close()
