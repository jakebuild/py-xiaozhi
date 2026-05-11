import asyncio
import socket
import logging
from src.core.plugin_manager import BasePlugin

logger = logging.getLogger(__name__)

class CustomIPCPlugin(BasePlugin):
    name = 'custom_ipc'
    description = 'Listens for UDP packets to trigger state machine events'
    
    def __init__(self):
        super().__init__()
        self.app = None
        self.transport = None
        
    class UDPProtocol(asyncio.DatagramProtocol):
        def __init__(self, app):
            self.app = app
            
        def datagram_received(self, data, addr):
            message = data.decode().strip()
            if message == 'press':
                logger.info('Received IPC press event! Triggering voice.')
                self.app.state_machine.handle_event('press')

    async def setup(self, app):
        self.app = app
        
    async def start(self):
        loop = asyncio.get_running_loop()
        try:
            self.transport, _ = await loop.create_datagram_endpoint(
                lambda: self.UDPProtocol(self.app),
                local_addr=('127.0.0.1', 9999)
            )
            logger.info('Custom IPC plugin started on UDP 9999')
            return True
        except Exception as e:
            logger.error(f'Failed to start IPC plugin: {e}')
            return False
            
    async def stop(self):
        if self.transport:
            self.transport.close()
