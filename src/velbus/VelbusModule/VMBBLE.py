from typing import Callable

import sanic.request
import sanic.response

from ._registry import register
from .NestedAddressVelbusModule import NestedAddressVelbusModule, VelbusModuleChannel
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.ModuleInfo import ModuleInfo
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
        "1": {...}  # channel state
        ...
    }
    """
    def __init__(self,
                 bus: VelbusProtocol,
                 address: int,
                 module_info: ModuleInfo = None,
                 ):
        if isinstance(module_info, VMB2BLE_MI):
            channels = [1, 2]
        elif isinstance(module_info, VMB1BLS_MI):
            channels = [1]
        else:
            raise NotImplementedError("Unreachable code")

        super().__init__(
            bus=bus,
            address=address,
            module_info=module_info,
            channels=channels, channel_type=VMBBLEChannel,
        )


class VMBBLEChannel(VelbusModuleChannel):
    """
            'status': 'down',
                      # 'up', 'off', 'down'
            'position': 100,
                        # Position of blind range 0..100 (inclusive). 0=up, 100=down
        },
        ...
    }
    """
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

            self.state = {
                'status': status,
                'position': blind_status.blind_position,
            }

        # TODO: add moving indicator

    async def _get_status(self, bus: VelbusProtocol):
        if 'status' not in self.state:
            _ = await bus.velbus_query(
                VelbusFrame(
                    address=self.address,
                    message=ModuleStatusRequest(
                        channel=1 << (self.channel - 1),
                    ),
                ),
                BlindStatusV2,
                additional_check=(lambda vbm: vbm.message.channel == self.channel),
            )
            # Do await the reply, but don't actually use it.
            # The reply will (also) be given to self.message(),
            # so by the time we get here, the cache will be up-to-date

        return self.state

    async def position_GET(self,
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

        status = await self._get_status(bus)

        return sanic.response.json(status['position'])

    async def position_PUT(self,
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
                channel=self.channel,
                position=requested_status,
            )
        elif isinstance(requested_status, str):
            if requested_status == 'up':
                message = SwitchBlindV2(
                    command=SwitchBlindV2.Command.SwitchBlindUp,
                    channel=self.channel,
                )
            elif requested_status == 'down':
                message = SwitchBlindV2(
                    command=SwitchBlindV2.Command.SwitchBlindDown,
                    channel=self.channel,
                )
            elif requested_status == 'stop':
                message = SwitchBlindOffV2(
                    channel=self.channel,
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
            additional_check=(lambda vbm: vbm.message.channel == self.channel),
        )

        return await self.position_GET(path_info, request, bus)
