from datetime import datetime

import sanic.request
import sanic.response

from ._registry import register
from .NestedAddressVelbusModule import NestedAddressVelbusModule
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage._types import BlindTimeout
from ..VelbusMessage.ModuleInfo.VMB2BL import VMB2BL as VMB2BL_MI
from ..VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from ..VelbusMessage.BlindStatus import BlindStatusV1
from ..VelbusMessage.SwitchBlind import SwitchBlindV1
from ..VelbusMessage.SwitchBlindOff import SwitchBlindOffV1

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
        1: {
            'status': 'down',
                      # 'up', 'off', 'down'
            'position': 100,
                        # ESTIMATED position of blind, range 0..100 (inclusive). 0=up, 100=down
        },
        ...
    }
    """

    def __init__(self, module_info, *args, **kwargs):
        super().__init__(*args, module_info=module_info, **kwargs)

        self.addresses = [1, 2]

        self.timeout = {
            1: BlindTimeout.to_secs(module_info.timeout_blind1),
            2: BlindTimeout.to_secs(module_info.timeout_blind2),
        }

        for blind in (1,2):
            self.state[str(blind)] = {
                'status': 'off',
                'position': 50,
            }

        self.estimate_info = {}
        for i in (1, 2):
            self.estimate_info[i] = {
                'timestamp': datetime.utcnow(),
            }

    def message(self, vbm: VelbusFrame):
        if isinstance(vbm.message, BlindStatusV1):
            blind_status = vbm.message

            current_position = self.estimate_position(blind_status.channel)
            self.estimate_info[blind_status.channel]['timestamp'] = datetime.utcnow()

            if blind_status.blind_status == BlindStatusV1.BlindStatus.Off:
                status = 'off'
            elif blind_status.blind_status in (BlindStatusV1.BlindStatus.Blind1Down,
                                               BlindStatusV1.BlindStatus.Blind2Down):
                status = 'down'
            elif blind_status.blind_status in (BlindStatusV1.BlindStatus.Blind1Up,
                                               BlindStatusV1.BlindStatus.Blind2Up):
                status = 'up'
            else:
                raise NotImplementedError("Unreachable code")

            self.state[str(blind_status.channel)] = {
                'status': status,
                'position': current_position,
            }

    def estimate_position(self, channel: int) -> int:
        if self.state[str(channel)]['status'] == 'off':
            # Blind was stopped, no movement to calculate
            return self.state[str(channel)]['position']
        # else: Blind was moving

        delta_t = datetime.utcnow() - self.estimate_info[channel]['timestamp']
        delta_t = delta_t.total_seconds()
        if self.state[str(channel)]['status'] == 'up':
            direction = -1  # up
        else:
            direction = 1  # down
        travel = direction * 100 * delta_t / self.timeout[channel]

        return clamp(
            self.state[str(channel)]['position'] + travel,
            0, 100)

    async def _get_status(self, bus: VelbusProtocol, channel):
        if str(channel) not in self.state:
            _ = await bus.velbus_query(
                VelbusFrame(
                    address=self.address,
                    message=ModuleStatusRequest(
                        channel=0b11 << 2*(channel - 1),
                    ),
                ),
                BlindStatusV1,
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

        _ = await self._get_status(bus, subaddress)

        return sanic.response.json(self.estimate_position(subaddress))

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
            current_position = self.estimate_position(subaddress)

            if requested_status == current_position:
                message = SwitchBlindOffV1(
                    channel=subaddress,
                )
            else:
                travel = int((requested_status - current_position) / 100 * self.timeout[subaddress])
                direction = SwitchBlindV1.Command.SwitchBlindDown if travel > 0 else SwitchBlindV1.Command.SwitchBlindUp
                travel = abs(travel)
                if travel == 0:
                    # timeout == 0 means use default, round up
                    travel = 1
                message = SwitchBlindV1(
                    command=direction,
                    channel=subaddress,
                    timeout=int(travel),
                )

        elif isinstance(requested_status, str):
            if requested_status == 'up':
                message = SwitchBlindV1(
                    command=SwitchBlindV1.Command.SwitchBlindUp,
                    channel=subaddress,
                )
            elif requested_status == 'down':
                message = SwitchBlindV1(
                    command=SwitchBlindV1.Command.SwitchBlindDown,
                    channel=subaddress,
                )
            elif requested_status == 'stop':
                message = SwitchBlindOffV1(
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
            BlindStatusV1,
            additional_check=(lambda vbm: vbm.message.channel == subaddress),
        )

        return await self.position_GET(subaddress, path_info, request, bus)
