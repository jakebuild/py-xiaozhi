import aiohttp
import logging
from src.iot.thing import Thing

logger = logging.getLogger(__name__)

class HomeKitSwitch(Thing):
    def __init__(self, name, accessory_id, webhook_port=51828):
        super().__init__(name, f"HomeKit Switch: {name}")
        self.accessory_id = accessory_id
        self.webhook_port = webhook_port
        self.power = False
        
        self.add_property("power", "Switch status", self.get_power)
        self.add_method("TurnOn", "Turn On", [], self._turn_on)
        self.add_method("TurnOff", "Turn Off", [], self._turn_off)

    async def get_power(self):
        return self.power

    async def _send_command(self, state: bool):
        url = f"http://localhost:{self.webhook_port}/?accessoryId={self.accessory_id}&state={str(state).lower()}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        self.power = state
                        return True
                    else:
                        logger.error(f"HomeKit Webhook failed: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error calling HomeKit Webhook: {e}")
            return False

    async def _turn_on(self, params):
        if await self._send_command(True):
            return {"status": "success", "message": f"{self.name} turned on"}
        return {"status": "error", "message": f"Failed to turn on {self.name}"}

    async def _turn_off(self, params):
        if await self._send_command(False):
            return {"status": "success", "message": f"{self.name} turned off"}
        return {"status": "error", "message": f"Failed to turn off {self.name}"}
