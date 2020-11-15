import dataclasses
import typing
import datetime

import sanic.request
import sanic.response

from .NestedAddressVelbusModule import NestedAddressVelbusModule, VelbusModuleChannel
from ._registry import register

from .. import HttpApi
from ..VelbusMessage.ModuleInfo.ModuleInfo import ModuleInfo
from ..VelbusMessage.ModuleInfo.VMB4RYNO import VMB4RYNO as VMB4RYNO_MI
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.RelayStatus import RelayStatus
from ..VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from ..VelbusMessage.SwitchRelay import SwitchRelay
from ..VelbusMessage.StartRelayTimer import StartRelayTimer
from ..VelbusMessage.PushButtonStatus import PushButtonStatus
from .VelbusModule import DelayedCall

from ..VelbusProtocol import VelbusProtocol, VelbusDelayedHttpProtocol


@dataclasses.dataclass
class RelayStep(DelayedCall):
    status: typing.Union[bool, int] = False

    @classmethod
    def from_any(cls, o: typing.Any):
        if isinstance(o, dict):
            return cls(**o)
        elif isinstance(o, bool) or isinstance(o, int):
            return cls(status=o)
        else:
            raise TypeError(f"Couldn't understand object of type {type(o)}: {repr(o)}")


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
                 ):
        super().__init__(
            bus=bus,
            address=address,
            module_info=module_info,
            channels=[1, 2, 3, 4, 5], channel_type=VMB4RYNOChannel,
        )


class VMB4RYNOChannel(VelbusModuleChannel):
    """
    VMB4RYNO channel

    state = {
        'relay': False,
                 # Current relay state
                 # either a boolean (On = True, Off = False, obviously)
                 # or an float representing the (fractional) Unix timestamp (UTC)
                 # on which the timer will expire.
        'last_change': 1600000000.
                       # float representing the (fractional) Unix timestamp (UTC)
                       # of the last change in `relay`.
                       # null or absent if not known.
    }
    """
    def message(self, vbm: VelbusFrame):
        previous_state = self.state.get('relay')

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

        if previous_state is not None and self.state['relay'] != previous_state:
            self.state['last_change'] = datetime.datetime.now().timestamp()

    async def _get_relay_state(self, bus: VelbusProtocol):
        if 'relay' not in self.state:
            channel_index = 1 << (self.channel - 1)
            _ = await bus.velbus_query(
                VelbusFrame(
                    address=self.address,
                    message=ModuleStatusRequest(
                        channel=channel_index,
                        # ModuleStatusRequest is generic UInt(8), Index-encoding needs to be done here
                    ),
                ),
                RelayStatus,
                additional_check=(lambda vbm: vbm.message.channel == self.channel),
                # ^^^ Index decoding is done in RelayStatus
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
        ret = self.e_relay_PUT(
            path_info=path_info,
            request=request,
            bus=bus,
            allow_simulated_behaviour=False,
        )
        if ret.status // 100 != 2:
            return ret
        # else: 2xx response, continue

        await self.delayed_calls[0].future  # wait for call to happen

        return await self.relay_GET(path_info, request, bus)

    def e_relay_PUT(self,
                    path_info: str,
                    request: sanic.request,
                    bus: VelbusProtocol,
                    allow_simulated_behaviour: bool = True,
                    ) -> sanic.response.HTTPResponse:
        if path_info != '':
            return sanic.response.text('Not found', status=404)

        try:
            requested_status = RelayStep.to_list(request.json)
        except TypeError as e:
            return sanic.response.text(f"Bad Request: {e}", 400)

        if len(requested_status) == 0:
            return sanic.response.text("Bad request: empty list", 400)
        if not allow_simulated_behaviour and not RelayStep.is_trivial(requested_status):
            return sanic.response.text('Bad request: non-native request on native endpoint', 400)

        try:
            self.delayed_calls = requested_status
        except ValueError as e:
            return sanic.response.text('Bad Request: could not parse PUT body: ' + str(e), 400)

        return sanic.response.text("OK", 202)

    def e_relay_GET(self,
                    path_info: str,
                    request: sanic.request,
                    bus: VelbusProtocol,
                    ) -> sanic.response.HTTPResponse:
        return self.delayed_calls_GET(path_info)

    async def delayed_call(self, relay_step: RelayStep) -> typing.Any:
        bus = VelbusDelayedHttpProtocol(original_timestamp=HttpApi.sanic_request_datetime.get(),
                                        request=HttpApi.sanic_request.get())
        if isinstance(relay_step.status, bool):
            message = SwitchRelay(
                command=SwitchRelay.Command.SwitchRelayOn if relay_step.status
                else SwitchRelay.Command.SwitchRelayOff,
                channel=self.channel,
            )
        elif isinstance(relay_step.status, int):
            message = StartRelayTimer(
                channel=self.channel,
                delay_time=relay_step.status,
            )
        else:
            raise TypeError(f"unknown type for status in RelayStep: {repr(relay_step)}")

        _ = await bus.velbus_query(
            VelbusFrame(
                address=self.address,
                message=message,
            ),
            RelayStatus,
            additional_check=(lambda vbm: vbm.message.channel == self.channel),
        )

        return relay_step.status

    async def last_change_GET(self,
                        path_info: str,
                        request: sanic.request,
                        bus: VelbusProtocol
                        ) -> sanic.response.HTTPResponse:
        """
        Returns the time of last change
        """
        del request  # unused

        if path_info != '':
            return sanic.response.text('Not found', status=404)

        return sanic.response.json(self.state.get('last_change'))
