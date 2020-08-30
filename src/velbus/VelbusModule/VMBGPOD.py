import time

import sanic.response

from ..utils import cache_control_max_age
from .VelbusModule import VelbusModule
from ._registry import register
from ..VelbusMessage.ModuleInfo.VMBGPOD import VMBGPOD as VMBGPOD_mi
from ..VelbusMessage.ModuleInfo.VMBGPO import VMBGPO as VMBGPO_mi
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.SensorTemperatureRequest import SensorTemperatureRequest
from ..VelbusMessage.SensorTemperature import SensorTemperature
from ..VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from ..VelbusMessage.TemperatureSensorStatus import TemperatureSensorStatus
from ..VelbusMessage.PushButtonStatus import PushButtonStatus

from ..VelbusProtocol import VelbusProtocol


@register(VMBGPOD_mi, VMBGPO_mi)
class VMBGPOD(VelbusModule):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def message(self, vbm: VelbusFrame):
        if isinstance(vbm.message, SensorTemperature):
            self.state['temperature']['timestamp'] = time.time()
            self.state['temperature']['value'] = vbm.message.current_temperature

        elif isinstance(vbm.message, PushButtonStatus):
            pb = {_: None for _ in range(8)}

            for i in range(8):
                # Velbus numbers from right to left
                if vbm.message.just_pressed[i]:
                    pb[str(8-i)] = True
                if vbm.message.long_pressed[i]:
                    pb[str(8-i)] = 'long'
                if vbm.message.just_released[i]:
                    pb[str(8-i)] = False

            self.state['pushbutton'] = pb

    async def _get_sensor_temperature(
            self,
            bus: VelbusProtocol,
            max_age: int = None,
    ):
        if max_age is None:
            max_age = 60

        now = time.time()
        min_timestap = now - max_age
        if self.state.get('temperature', {'timestamp': 0})['timestamp'] < min_timestap:
            await bus.velbus_query(
                VelbusFrame(
                    address=self.address,
                    message=SensorTemperatureRequest(),
                ),
                SensorTemperature,
            )
            # do await, but don't actually use the value
            # by the time we get here, message() will have populated the cache

        return self.state

    async def temperature_GET(self, path_info, request, bus: VelbusProtocol):
        max_age = cache_control_max_age(request)
        status = await self._get_sensor_temperature(bus=bus, max_age=max_age)
        age = int(time.time() - status['temperature']['timestamp'])

        return sanic.response.json(
            status['temperature']['value'],
            headers={
                'Age': age,
            }
        )

    async def set_temperature_GET(self, path_info, request, bus: VelbusProtocol):
        # TODO: implement cache
        sensor_status = await bus.velbus_query(
            VelbusFrame(
                address=self.address,
                message=ModuleStatusRequest(),
            ),
            TemperatureSensorStatus,
        )

        return sanic.response.json(sensor_status.message.set_temperature)
