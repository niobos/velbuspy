import sanic.request
import sanic.response

from ._registry import register
from .NestedAddressVelbusModule import NestedAddressVelbusModule
from ..VelbusMessage.ModuleInfo.VMB4DC import VMB4DC as VMB4DC_MI
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.DimmercontrollerStatus import DimmercontrollerStatus
from ..VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from ..VelbusMessage.SetDimvalue import SetDimvalue

from ..VelbusProtocol import VelbusProtocol


@register(VMB4DC_MI)
class VMB4DC(NestedAddressVelbusModule):
    """
    VMB4DC module management

    state = {
        1: {
            'dimvalue': 100,
                        # Current dim value range 0..100 (inclusive)
        },
        ...
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addresses = [1, 2, 3, 4]

    def message(self, vbm: VelbusFrame):
        if isinstance(vbm.message, DimmercontrollerStatus):
            dimmer_status = vbm.message

            self.state[str(dimmer_status.channel)] = {
                'dimvalue': dimmer_status.dimvalue,
                # 'status': relay_status.disabled_inhibit_force,
                # 'led_status': relay_status.led_status,
                # 'timeout': datetime.datetime.now() + datetime.timedelta(seconds=dimmer_status.delay_time)
            }

    async def _get_status(self, bus: VelbusProtocol, channel):
        if str(channel) not in self.state:
            _ = await bus.velbus_query(
                VelbusFrame(
                    address=self.address,
                    message=ModuleStatusRequest(
                        channel=1 << (channel - 1),
                    ),
                ),
                DimmercontrollerStatus,
                additional_check=(lambda vbm: vbm.message.channel == channel),
            )
            # Do await the reply, but don't actually use it.
            # The reply will (also) be given to self.message(),
            # so by the time we get here, the cache will be up-to-date

        return self.state[str(channel)]

    async def dimvalue_GET(self,
                           subaddress: int,
                           path_info: str,
                           request: sanic.request,
                           bus: VelbusProtocol
                           ) -> sanic.response.HTTPResponse:
        """
        Returns the current state of the dimmer.
        """
        del request  # unused

        if path_info != '':
            return sanic.response.text('Not found', status=404)

        status = await self._get_status(bus, subaddress)

        return sanic.response.json(status['dimvalue'])

    async def dimvalue_PUT(self,
                           subaddress: int,
                           path_info: str,
                           request: sanic.request,
                           bus: VelbusProtocol
                           ) -> sanic.response.HTTPResponse:
        """
        Set the dim value
        """
        if path_info != '':
            return sanic.response.text('Not found', status=404)

        requested_status = request.json
        if isinstance(requested_status, int):
            message = SetDimvalue(
                channel=subaddress,
                dimvalue=requested_status,
                dimspeed=0,
            )
        else:
            return sanic.response.text('Bad Request: could not parse PUT body as int', 400)

        _ = await bus.velbus_query(
            VelbusFrame(
                address=self.address,
                message=message,
            ),
            DimmercontrollerStatus,
            additional_check=(lambda vbm: vbm.message.channel == subaddress),
        )

        return await self.dimvalue_GET(subaddress, path_info, request, bus)
