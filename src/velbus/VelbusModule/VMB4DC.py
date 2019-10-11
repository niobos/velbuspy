import dataclasses
import typing

import dateutil.parser
import sanic.request
import sanic.response

from ._registry import register
from . import VelbusModule
from .NestedAddressVelbusModule import NestedAddressVelbusModule, VelbusModuleChannel
from ..VelbusMessage.ModuleInfo.ModuleInfo import ModuleInfo
from ..VelbusMessage.ModuleInfo.VMB4DC import VMB4DC as VMB4DC_MI
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.DimmercontrollerStatus import DimmercontrollerStatus
from ..VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from ..VelbusMessage.SetDimvalue import SetDimvalue
from ..VelbusProtocol import VelbusProtocol, VelbusDelayedHttpProtocol
from .. import HttpApi


class NonNative(Exception):
    """
    Exception raised when behaviour was requested that is available, but simulated
    by this daemon, as opposed to native to the module.
    """
    pass


@dataclasses.dataclass()
class DimStep(VelbusModule.DelayedCall):
    dimvalue: int  # 0-100
    dimspeed: int = 0  # 0-65536 seconds

    @classmethod
    def from_dict(cls, d: dict) -> "DimStep":
        when = d.pop('when', None)
        if when is not None:
            when = dateutil.parser.parse(when)
        return cls(when=when, **d)  # may raise


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

    def __init__(self,
                 bus: VelbusProtocol,
                 address: int,
                 module_info: ModuleInfo = None,
                 update_state_cb: typing.Callable = lambda ops: None
                 ):
        super().__init__(
            bus=bus,
            address=address,
            module_info=module_info,
            channels=[1, 2, 3, 4], channel_type=VMB4DCChannel,
            update_state_cb=update_state_cb,
        )


class VMB4DCChannel(VelbusModuleChannel):
    """single channel of VMB4DC"""
    def __init__(self,
                 bus: VelbusProtocol,
                 channel: int,
                 parent_module: VMB4DC,
                 update_state_cb: typing.Callable = lambda ops: None,
                 ):
        super().__init__(
            bus=bus,
            channel=channel,
            parent_module=parent_module,
            update_state_cb=update_state_cb,
        )

    def message(self, vbm: VelbusFrame):
        if isinstance(vbm.message, DimmercontrollerStatus):
            dimmer_status = vbm.message

            if dimmer_status.channel == self.channel:
                self.state = {
                    'dimvalue': dimmer_status.dimvalue,
                    # 'status': relay_status.disabled_inhibit_force,
                    # 'led_status': relay_status.led_status,
                    # 'timeout': datetime.datetime.now() + datetime.timedelta(seconds=dimmer_status.delay_time)
                }

    async def _get_status(self, bus: VelbusProtocol):
        if "dimvalue" not in self.state:
            _ = await bus.velbus_query(
                VelbusFrame(
                    address=self.address,
                    message=ModuleStatusRequest(
                        channel=1 << (self.channel - 1),
                    ),
                ),
                DimmercontrollerStatus,
                additional_check=(lambda vbm: vbm.message.channel == self.channel),
            )
            # Do await the reply, but don't actually use it.
            # The reply will (also) be given to self.message(),
            # so by the time we get here, the cache will be up-to-date

        return self.state

    async def dimvalue_GET(self,
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

        status = await self._get_status(bus)

        return sanic.response.json(status['dimvalue'])

    async def dimvalue_PUT(self,
                           path_info: str,
                           request: sanic.request,
                           bus: VelbusProtocol
                           ) -> sanic.response.HTTPResponse:
        """
        Set the dim value
        """
        try:
            return await self.e_dimvalue_PUT(
                path_info=path_info,
                request=request,
                bus=bus,
                allow_simulated_behaviour=False,
            )
        except NonNative:
            return sanic.response.text('Bad Request: non-native request on native endpoint', 400)

    async def delayed_call(self, dim_step: DimStep) -> typing.Any:
        bus = VelbusDelayedHttpProtocol(original_timestamp=HttpApi.sanic_request_datetime.get(),
                                        request=HttpApi.sanic_request.get())
        _ = await bus.velbus_query(
            VelbusFrame(
                address=self.address,
                message=SetDimvalue(
                    channel=self.channel,
                    dimvalue=dim_step.dimvalue,
                    dimspeed=dim_step.dimspeed,
                ),
            ),
            DimmercontrollerStatus,
            additional_check=(lambda vbm: vbm.message.channel == self.channel),
        )

        return dim_step.dimvalue

    async def e_dimvalue_PUT(self,
                             path_info: str,
                             request: sanic.request,
                             bus: VelbusProtocol,
                             allow_simulated_behaviour: bool = True,
                             ) -> sanic.response.HTTPResponse:
        """
        Enhanced dimvalue endpoint.
        Some features are simulated by this daemon, they are not executed
        by the Velbus module. If allow_simulated_behaviour is not True,
        a NonNative exception is raised in this case.
        """
        if path_info != '':
            return sanic.response.text('Not found', status=404)

        requested_status = request.json

        if isinstance(requested_status, int):
            requested_status = {
                'dimvalue': requested_status
            }

        if isinstance(requested_status, dict):
            requested_status = [
                requested_status
            ]

        if isinstance(requested_status, list):
            try:
                requested_status = [
                    DimStep.from_dict(s)
                    for s in requested_status
                ]
            except TypeError as e:
                return sanic.response.text(f"Bad Request: {e}", 400)

            if len(requested_status) == 0:
                return sanic.response.text("Bad request: empty list", 400)
            if not allow_simulated_behaviour:
                if len(requested_status) > 1:
                    raise NonNative()
                if requested_status[0].when is not None:
                    raise NonNative()

        else:
            return sanic.response.text('Bad Request: could not parse PUT body', 400)

        try:
            self.delayed_calls = requested_status
        except ValueError as e:
            return sanic.response.text('Bad Request: could not parse PUT body: ' + str(e), 400)

        return sanic.response.text("OK", 202)

    async def e_dimvalue_GET(self,
                             path_info: str,
                             request: sanic.request,
                             bus: VelbusProtocol
                             ) -> sanic.response.HTTPResponse:
        return sanic.response.json([
            call.as_dict()
            for call in self.delayed_calls
        ])
