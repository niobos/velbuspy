import sanic.response

from .VelbusModule import VelbusModule
from ._registry import register
from ..VelbusMessage.ModuleInfo.VMBGPOD import VMBGPOD as VMBGPOD_mi
from ..VelbusMessage.ModuleInfo.VMBGPO import VMBGPO as VMBGPO_mi
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.SensorTemperatureRequest import SensorTemperatureRequest
from ..VelbusMessage.SensorTemperature import SensorTemperature
from ..VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from ..VelbusMessage.TemperatureSensorStatus import TemperatureSensorStatus

from ..VelbusProtocol import VelbusProtocol


@register(VMBGPOD_mi, VMBGPO_mi)
class VMBGPOD(VelbusModule):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # TODO: implement message() and cache

    async def temperature_GET(self, path_info, request, bus: VelbusProtocol):
        sensor_temp = await bus.velbus_query(
            VelbusFrame(
                address=self.address,
                message=SensorTemperatureRequest(),
            ),
            SensorTemperature,
        )

        return sanic.response.json(sensor_temp.message.current_temperature)

    async def set_temperature_GET(self, path_info, request, bus: VelbusProtocol):
        sensor_status = await bus.velbus_query(
            VelbusFrame(
                address=self.address,
                message=ModuleStatusRequest(),
            ),
            TemperatureSensorStatus,
        )

        return sanic.response.json(sensor_status.message.set_temperature)
