from datetime import datetime
import typing

import sanic.request
import sanic.response

from ._registry import register
from .NestedAddressVelbusModule import NestedAddressVelbusModule, VelbusModuleChannel
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage._types import BlindTimeout
from ..VelbusMessage.ModuleInfo.ModuleInfo import ModuleInfo
from ..VelbusMessage.ModuleInfo.VMB2BL import VMB2BL as VMB2BL_MI
from ..VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from ..VelbusMessage.BlindStatus import BlindStatusV1
from ..VelbusMessage.SwitchBlind import SwitchBlindV1
from ..VelbusMessage.SwitchBlindOff import SwitchBlindOffV1
from ..VelbusModule.VelbusModule import VelbusModule

from ..VelbusProtocol import VelbusProtocol


def clamp(v, min_v, max_v):
    if v < min_v:
        return min_v
    elif v > max_v:
        return max_v
    else:
        return v


@register(VMB2BL_MI)
class VMB2BL(NestedAddressVelbusModule):
    """
    VMB2BL module management

    state = {
        "1": {...},   # channel state
        ...
    }
    """
    def __init__(self,
                 bus: VelbusProtocol,
                 address: int,
                 module_info: ModuleInfo = None,
                 ):
        self.module_info = module_info  # Save module_info to extract timeout settings
        # NOTE: save module_info before calling super()
        super().__init__(
            bus=bus,
            address=address,
            module_info=module_info,
            channels=[1, 2], channel_type=VMBBLChannel,
        )


class VMBBLChannel(VelbusModuleChannel):
    """
            'status': 'down',
                      # 'up', 'off', 'down'
            'position': 100,
                        # ESTIMATED position of blind, range 0..100 (inclusive). 0=up, 100=down
        },
        ...
    }
    """
    def __init__(self,
                 bus: VelbusProtocol,
                 channel: int,
                 parent_module: VMB2BL,
                 ):

        super().__init__(
            bus=bus,
            channel=channel,
            parent_module=parent_module,
        )
        if channel == 1:
            self.timeout = BlindTimeout.to_secs(parent_module.module_info.timeout_blind1)
        elif channel == 2:
            self.timeout = BlindTimeout.to_secs(parent_module.module_info.timeout_blind2)
        else:
            raise ValueError(f"Invalid channel for VMB2BL: {channel}")

        self.estimate_info = {
            'timestamp': datetime.utcnow(),
        }

    def message(self, vbm: VelbusFrame):
        if isinstance(vbm.message, BlindStatusV1):
            blind_status = vbm.message

            self.state['position'] = self.estimate_position()
            self.estimate_info['timestamp'] = datetime.utcnow()

            if blind_status.blind_status == BlindStatusV1.BlindStatus.Off:
                self.state['status'] = 'off'
            elif blind_status.blind_status in (BlindStatusV1.BlindStatus.Blind1Down,
                                               BlindStatusV1.BlindStatus.Blind2Down):
                self.state['status'] = 'down'
            elif blind_status.blind_status in (BlindStatusV1.BlindStatus.Blind1Up,
                                               BlindStatusV1.BlindStatus.Blind2Up):
                self.state['status'] = 'up'
            else:
                raise ValueError("Unknown blindstatus")

    def estimate_position(self) -> int:
        self.state.setdefault('status', 'off')
        self.state.setdefault('position', 50)

        if self.state['status'] == 'off':
            # Blind was stopped, no movement to calculate
            return self.state['position']
        # else: Blind was moving

        delta_t = datetime.utcnow() - self.estimate_info['timestamp']
        delta_t = delta_t.total_seconds()
        if self.state['status'] == 'up':
            direction = -1  # up
        else:
            direction = 1  # down
        travel = direction * 100 * delta_t / self.timeout

        return clamp(
            self.state['position'] + travel,
            0, 100)

    async def _get_status(self, bus: VelbusProtocol):
        if 'status' not in self.state:
            _ = await bus.velbus_query(
                VelbusFrame(
                    address=self.address,
                    message=ModuleStatusRequest(
                        channel=0b11 << 2*(self.channel - 1),
                    ),
                ),
                BlindStatusV1,
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

        # Assume we have up-to-date state. (We initialize to 50%, but can't check anyway)

        return sanic.response.json(self.estimate_position())

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
            current_position = self.estimate_position()

            if requested_status == current_position:
                message = SwitchBlindOffV1(
                    channel=self.channel,
                )
            else:
                travel = int((requested_status - current_position) / 100 * self.timeout)
                direction = SwitchBlindV1.Command.SwitchBlindDown if travel > 0 else SwitchBlindV1.Command.SwitchBlindUp
                travel = abs(travel)
                if travel == 0:
                    # timeout == 0 means use default, round up
                    travel = 1
                message = SwitchBlindV1(
                    command=direction,
                    channel=self.channel,
                    timeout=int(travel),
                )

        elif isinstance(requested_status, str):
            if requested_status == 'up':
                message = SwitchBlindV1(
                    command=SwitchBlindV1.Command.SwitchBlindUp,
                    channel=self.channel,
                )
            elif requested_status == 'down':
                message = SwitchBlindV1(
                    command=SwitchBlindV1.Command.SwitchBlindDown,
                    channel=self.channel,
                )
            elif requested_status == 'stop':
                message = SwitchBlindOffV1(
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
            BlindStatusV1,
            additional_check=(lambda vbm: vbm.message.channel == self.channel),
        )

        return await self.position_GET(path_info, request, bus)
