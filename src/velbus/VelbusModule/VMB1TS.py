import typing

import sanic.request
import sanic.response

from ._registry import register
from .VelbusModule import VelbusModule
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.ModuleInfo.VMB1TS import VMB1TS as VMB1TS_mi
from ..VelbusMessage.SensorTemperatureRequest import SensorTemperatureRequest
from ..VelbusMessage.SensorTemperature import SensorTemperature
from ..VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from ..VelbusMessage.TemperatureSensorStatus import TemperatureSensorStatus
from ..VelbusMessage.PushButtonStatus import PushButtonStatus

from ..VelbusProtocol import VelbusProtocol


@register(VMB1TS_mi)
class VMB1TS(VelbusModule):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def message(self, vbm: VelbusFrame):
        if isinstance(vbm.message, TemperatureSensorStatus):
            self.state['heater'] = bool(vbm.message.heater)

        elif isinstance(vbm.message, PushButtonStatus):
            if vbm.message.just_pressed[0]:
                self.state['heater'] = True

            if vbm.message.just_released[0]:
                self.state['heater'] = False

    # TODO: cache this
    async def temperature_GET(self, path_info, request, bus: VelbusProtocol):
        sensor_temp = await bus.velbus_query(
            VelbusFrame(
                address=self.address,
                message=SensorTemperatureRequest()
            ),
            SensorTemperature,
        )

        return sanic.response.json(sensor_temp.message.current_temperature)

    # TODO: cache this
    async def set_temperature_GET(self, path_info, request, bus: VelbusProtocol):
        sensor_status = await bus.velbus_query(
            VelbusFrame(
                address=self.address,
                message=ModuleStatusRequest(),
            ),
            TemperatureSensorStatus,
        )

        return sanic.response.json(sensor_status.message.set_temperature)

    async def _get_output_state(self, bus: VelbusProtocol) -> typing.Dict:
        if 'heater' not in self.state:
            await bus.velbus_query(
                VelbusFrame(
                    address=self.address,
                    message=ModuleStatusRequest(),
                ),
                TemperatureSensorStatus,
            )
            # Do await the reply, but don't actually use it.
            # The reply will (also) be given to self.message(),
            # so by the time we get here, the cache will be up-to-date

        return self.state

    async def heater_GET(
            self,
            path_info: str,
            request: sanic.request.Request,
            bus: VelbusProtocol,
    ) -> sanic.response.HTTPResponse:
        del path_info  # unused
        del request  # unused

        status = await self._get_output_state(bus)

        return sanic.response.json(status['heater'])
