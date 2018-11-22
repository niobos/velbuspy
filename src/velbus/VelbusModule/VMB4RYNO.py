from typing import Callable

import sanic.request
import sanic.response
import datetime


from .NestedAddressVelbusModule import NestedAddressVelbusModule, VelbusModuleChannel
from ._registry import register

from ..VelbusMessage.ModuleInfo.ModuleInfo import ModuleInfo
from ..VelbusMessage.ModuleInfo.VMB4RYNO import VMB4RYNO as VMB4RYNO_MI
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.RelayStatus import RelayStatus
from ..VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from ..VelbusMessage.SwitchRelay import SwitchRelay
from ..VelbusMessage.StartRelayTimer import StartRelayTimer
from ..VelbusMessage.PushButtonStatus import PushButtonStatus

from ..VelbusProtocol import VelbusProtocol


@register(VMB4RYNO_MI)
class VMB4RYNO(NestedAddressVelbusModule):
    """
    VMB4RYNO module management

    state = {
        "1": {...}  # channel state
        ...
    }
    """
    def __init__(self,
                 bus: VelbusProtocol,
                 address: int,
                 module_info: ModuleInfo = None,
                 update_state_cb: Callable = lambda ops: None
                 ):
        super().__init__(
            bus=bus,
            address=address,
            module_info=module_info,
            update_state_cb=update_state_cb,
            channels=[1, 2, 3, 4, 5], channel_type=VMB4RYNOChannel,
        )


class VMB4RYNOChannel(VelbusModuleChannel):
    """
    VMB4RYNO channel

    state = {
        'relay': False
                 # Current relay state
                 # either a boolean (On = True, Off = False, obviously)
                 # or an float representing the (fractional) Unix timestamp (UTC)
                 # on which the timer will expire.
    }
    """
    def message(self, vbm: VelbusFrame):
        if isinstance(vbm.message, RelayStatus):
            relay_status = vbm.message

            if relay_status.delay_timer == 0:
                self.state['relay'] = \
                    (relay_status.relay_status == relay_status.RelayStatus.On)

            else:  # timer running
                timeout = (datetime.datetime.now()
                           + datetime.timedelta(seconds=relay_status.delay_timer)
                           ).timestamp()
                self.state['relay'] = timeout

        elif isinstance(vbm.message, PushButtonStatus):
            push_button_status = vbm.message

            if push_button_status.just_pressed[8-self.channel]:  # relays are ordered LSb -> MSb
                if isinstance(self.state['relay'], bool):
                    self.state['relay'] = True
                # else: don't overwrite a running timer.

            if push_button_status.just_released[8-self.channel]:
                self.state['relay'] = False

    async def _get_relay_state(self, bus: VelbusProtocol):
        if 'relay' not in self.state:
            _ = await bus.velbus_query(
                VelbusFrame(
                    address=self.address,
                    message=ModuleStatusRequest(
                        channel=1 << (self.channel - 1),
                    ),
                ),
                RelayStatus,
                additional_check=(lambda vbm: vbm.message.relay == self.channel),
            )
            # Do await the reply, but don't actually use it.
            # The reply will (also) be given to self.message(),
            # so by the time we get here, the cache will be up-to-date
            # may raise

        return self.state

    async def relay_GET(self,
                        path_info: str,
                        request: sanic.request,
                        bus: VelbusProtocol
                        ) -> sanic.response.HTTPResponse:
        """
        Returns the current state of the relay. Either as a boolean,
        or as the number of seconds remaining on the timer (which usually
        evaluates to True as well)
        """
        del request  # unused

        if path_info != '':
            return sanic.response.text('Not found', status=404)

        status = await self._get_relay_state(bus)

        return sanic.response.json(status['relay'])

    async def relay_PUT(self,
                        path_info: str,
                        request: sanic.request,
                        bus: VelbusProtocol
                        ) -> sanic.response.HTTPResponse:
        """
        Set the relay status to either True or False,
        or an integer, which is interpreted as a timeout in seconds
        """
        if path_info != '':
            return sanic.response.text('Not found', status=404)

        requested_status = request.json
        if isinstance(requested_status, bool):
            message = SwitchRelay(
                command=SwitchRelay.Command.SwitchRelayOn if requested_status
                else SwitchRelay.Command.SwitchRelayOff,
                channel=self.channel,
            )
        elif isinstance(requested_status, int):
            message = StartRelayTimer(
                channel=self.channel,
                delay_time=requested_status,
            )
        else:
            return sanic.response.text('Bad Request: could not parse PUT body as int or bool', 400)

        _ = await bus.velbus_query(
            VelbusFrame(
                address=self.address,
                message=message,
            ),
            RelayStatus,
            additional_check=(lambda vbm: vbm.message.relay == self.channel),
        )
        # Wait for reply, but don't actually use it
        # self.message() will be called with the same reply. Processing happens there
        # May raise

        return await self.relay_GET(path_info, request, bus)
