import sanic.request
import sanic.response

from ._registry import register
from ._utils import validate_channel_from_pathinfo
from .VelbusModule import VelbusModule
from .NestedAddressVelbusModule import NestedAddressVelbusModule
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.ModuleInfo.VMB2BLE import VMB2BLE as VMB2BLE_MI
from ..VelbusMessage.ModuleInfo.VMB1BLS import VMB1BLS as VMB1BLS_MI
from ..VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from ..VelbusMessage.BlindStatus import BlindStatusV2
from ..VelbusMessage.SetBlindPosition import SetBlindPosition
from ..VelbusMessage.SwitchBlind import SwitchBlindV2
from ..VelbusMessage.SwitchBlindOff import SwitchBlindOffV2

from ..VelbusProtocol import VelbusProtocol


@register(VMB2BLE_MI, VMB1BLS_MI)
class VMBBLE(NestedAddressVelbusModule):
    """
    VMB2BLE and VMB1BLS module management

    state = {
        1: {
            'status': 'down',
                      # 'up', 'off', 'down'
            'position': 100,
                        # Position of blind range 0..100 (inclusive). 0=up, 100=down
        },
        ...
    }
    """

    def __init__(self, module_info, *args, **kwargs):
        super().__init__(*args, module_info=module_info, **kwargs)
        if isinstance(module_info, VMB2BLE_MI):
            self.addresses = [1, 2]
        elif isinstance(module_info, VMB1BLS_MI):
            self.addresses = [1]
        else:
            raise NotImplementedError("Unreachable code")

    def message(self, vbm: VelbusFrame):
        if isinstance(vbm.message, BlindStatusV2):
            blind_status = vbm.message

            if blind_status.blind_status == BlindStatusV2.BlindStatus.Off:
                status = 'off'
            elif blind_status.blind_status == BlindStatusV2.BlindStatus.Down:
                status = 'down'
            elif blind_status.blind_status == BlindStatusV2.BlindStatus.Up:
                status = 'up'
            else:
                raise NotImplementedError("Unreachable code")

            self.state[str(blind_status.channel)] = {
                'status': status,
                'position': blind_status.blind_position,
            }

        # TODO: add moving indicator

    async def _get_status(self, bus: VelbusProtocol, channel):
        if channel not in self.state:
            _ = await bus.velbus_query(
                VelbusFrame(
                    address=self.address,
                    message=ModuleStatusRequest(
                        channel=1 << (channel - 1),
                    ),
                ),
                BlindStatusV2,
                additional_check=(lambda vbm: vbm.message.channel == channel),
            )
            # Do await the reply, but don't actually use it.
            # The reply will (also) be given to self.message(),
            # so by the time we get here, the cache will be up-to-date

        return self.state[str(channel)]

    async def position_GET(self,
                           subaddress: int,
                           path_info: str,
                           request: sanic.request,
                           bus: VelbusProtocol
                           ) -> sanic.response.HTTPResponse:
        """
        Returns the current position of the blind in %.
        100% means down.
        """
        del request  # unused

        if path_info != '':
            return sanic.response.text('Not found', status=404)

        status = await self._get_status(bus, subaddress)

        return sanic.response.json(status['position'])

    async def position_PUT(self,
                           subaddress: int,
                           path_info: str,
                           request: sanic.request,
                           bus: VelbusProtocol
                           ) -> sanic.response.HTTPResponse:
        """
        Sets position of the blind in %.
        100% means down.
        """
        if path_info != '':
            return sanic.response.text('Not found', status=404)

        if request.body == b'up' or request.body == b'0':  # Special cases
            requested_status = 'up'
        elif request.body == b'down' or request.body == b'100':
            requested_status = 'down'
        elif request.body == b'stop':
            requested_status = 'stop'
        else:
            requested_status = request.json

        if isinstance(requested_status, int):
            message = SetBlindPosition(
                channel=subaddress,
                position=requested_status,
            )
        elif isinstance(requested_status, str):
            if requested_status == 'up':
                message = SwitchBlindV2(
                    command=SwitchBlindV2.Command.SwitchBlindUp,
                    channel=subaddress,
                )
            elif requested_status == 'down':
                message = SwitchBlindV2(
                    command=SwitchBlindV2.Command.SwitchBlindDown,
                    channel=subaddress,
                )
            elif requested_status == 'stop':
                message = SwitchBlindOffV2(
                    channel=subaddress,
                )
            else:
                raise AssertionError("Unreachable code reached")

        else:
            return sanic.response.text('Bad Request: could not parse PUT body as int', 400)

        _ = await bus.velbus_query(
            VelbusFrame(
                address=self.address,
                message=message,
            ),
            BlindStatusV2,
            additional_check=(lambda vbm: vbm.message.channel == subaddress),
        )

        return await self.position_GET(subaddress, path_info, request, bus)
