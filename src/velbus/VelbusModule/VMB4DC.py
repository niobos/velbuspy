import asyncio
from typing import List, Callable, Union

import sanic.request
import sanic.response
import attr

from ._registry import register
from .NestedAddressVelbusModule import NestedAddressVelbusModule, VelbusModuleChannel
from ..VelbusMessage.ModuleInfo.ModuleInfo import ModuleInfo
from ..VelbusMessage.ModuleInfo.VMB4DC import VMB4DC as VMB4DC_MI
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.DimmercontrollerStatus import DimmercontrollerStatus
from ..VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from ..VelbusMessage.SetDimvalue import SetDimvalue
from ..VelbusProtocol import VelbusProtocol, VelbusDelayedProtocol


class NonNative(Exception):
    pass


@attr.s(slots=True, auto_attribs=True)
class DimStep:
    dimvalue: int  # 0-100
    dimspeed: int = 0  # 0-65536 seconds
    timeout: int = 0  # duration of this step in seconds


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
                 update_state_cb: Callable = lambda ops: None
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
                 update_state_cb: Callable = lambda ops: None,
                 ):
        super().__init__(
            bus=bus,
            channel=channel,
            parent_module=parent_module,
            update_state_cb=update_state_cb,
        )
        self.queue: List[DimStep] = []
        self.queue_processing_task: asyncio.Task = asyncio.Future()
        self.queue_processing_task.set_result(None)  # Initialize to a Done "task"

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
                raise_non_native=True,
            )
        except NonNative:
            return sanic.response.text('Bad Request: non-native request on native endpoint', 400)

    async def process_queue(self,
                            bus: VelbusProtocol):
        while len(self.queue):
            next_step = self.queue.pop(0)

            _ = await bus.velbus_query(
                VelbusFrame(
                    address=self.address,
                    message=SetDimvalue(
                        channel=self.channel,
                        dimvalue=next_step.dimvalue,
                        dimspeed=next_step.dimspeed,
                    ),
                ),
                DimmercontrollerStatus,
                additional_check=(lambda vbm: vbm.message.channel == self.channel),
            )

            await asyncio.sleep(next_step.timeout)

    async def e_dimvalue_PUT(self,
                             path_info: str,
                             request: sanic.request,
                             bus: VelbusProtocol,
                             raise_non_native: bool = False,
                             ) -> sanic.response.HTTPResponse:
        """
        Enhanced dimvalue endpoint.
        Some features are simulated by this daemon, they are not executed
        by the Velbus module.
        """
        if path_info != '':
            return sanic.response.text('Not found', status=404)

        requested_status = request.json

        if isinstance(requested_status, int):
            requested_status = [
                DimStep(
                    dimvalue=requested_status,
                )
            ]

        elif isinstance(requested_status, dict):
            try:
                requested_status = [
                    DimStep(**requested_status)
                ]
            except TypeError as e:
                return sanic.response.text(f"Bad Request: {e}", 400)

        elif isinstance(requested_status, list):
            try:
                requested_status = [
                    DimStep(**s)
                    for s in requested_status
                ]
            except TypeError as e:
                return sanic.response.text(f"Bad Request: {e}", 400)
            if len(requested_status) == 0:
                return sanic.response.text("Bad request: empty list", 400)
            elif len(requested_status) > 1:
                if raise_non_native:
                    raise NonNative()

        else:
            return sanic.response.text('Bad Request: could not parse PUT body', 400)

        if not self.queue_processing_task.done():
            self.queue_processing_task.cancel()
        self.queue = requested_status
        self.queue_processing_task = asyncio.get_event_loop().create_task(
            self.process_queue(
                bus=VelbusDelayedProtocol(bus),
            ))

        return sanic.response.text("OK", 202)
