import dataclasses
import typing

import sanic.request
import sanic.response

from .NestedAddressVelbusModule import NestedAddressVelbusModule, VelbusModuleChannel
from ._registry import register
from . import VelbusModule
from ..VelbusMessage.ModuleInfo.ModuleInfo import ModuleInfo
from ..VelbusMessage.ModuleInfo.VMBDALI import VMBDALI as VMBDALI_MI
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.SetDimvalue import SetDimvalue_VMBDALI
from ..VelbusMessage.DaliDeviceSettingsRequest import DaliDeviceSettingsRequest
from ..VelbusMessage.DaliDeviceSettings import DaliDeviceSettings
from ..VelbusProtocol import VelbusProtocol, VelbusDelayedHttpProtocol, VelbusHttpProtocol
from .. import HttpApi


class NonNative(Exception):
    """
    Exception raised when behaviour was requested that is available, but simulated
    by this daemon, as opposed to native to the module.
    """
    pass


@dataclasses.dataclass()
class DimStep(VelbusModule.DelayedCall):
    dimvalue: int = 0  # 0-254 (255=keep current value)

    @classmethod
    def from_any(cls, o: typing.Any):
        if isinstance(o, dict):
            return cls(**o)
        elif isinstance(o, int):
            return cls(dimvalue=o)
        else:
            raise TypeError(f"Couldn't understand object of type {type(o)}: {repr(o)}")


@register(VMBDALI_MI)
class VMBDALI(NestedAddressVelbusModule):
    """
    VMBDALI module management

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
            channels=list(range(1, 96+1)), channel_type=VMBDALIChannel,
        )


class VMBDALIChannel(VelbusModuleChannel):
    """
    VMBDALI channel

    state = {
    }
    """
    def message(self, vbm: VelbusFrame):
        # TODO: process relevant messages for state
        # VMBDALI does not seem to send much relevant info...
        pass

        # interesting messages are
        # [e8 <dali_addr> 1a <current dim value>]
        #   triggered by [e7 <dali_addr> 00] (from cache, estimated)
        #             or [e7 <dali_addr> 01] (polled over DALI)

    async def delayed_call(self, dim_step: DimStep) -> typing.Any:
        bus = VelbusDelayedHttpProtocol(original_timestamp=HttpApi.sanic_request_datetime.get(),
                                        request=HttpApi.sanic_request.get())
        _ = await bus.process_message(
            VelbusFrame(
                address=self.address,
                message=SetDimvalue_VMBDALI(
                    channel=self.channel,
                    dimvalue=dim_step.dimvalue,
                ),
            ),
        )
        # VMBDALI does not respond to SetDimvalue
        # TODO: verify that it actually worked?

        return dim_step.dimvalue

    # Don't do this (yet). This may hang the VMBDALI module if the DALI-address is unreachable
    # async def dimvalue_GET(self,
    #                        path_info: str,
    #                        request: sanic.request,
    #                        bus: VelbusProtocol,
    #                        ) -> sanic.response.HTTPResponse:
    #     del request  # use HttpApi.sanic_request.get() instead
    #     del bus
    #     bus = VelbusHttpProtocol(HttpApi.sanic_request.get())
    #
    #     if path_info != '':
    #         return sanic.response.text('Not found', status=404)
    #
    #     message = DaliDeviceSettingsRequest(
    #         channel=self.channel,
    #         source=DaliDeviceSettingsRequest.Source.Device,
    #     )
    #     resp = await bus.velbus_query(
    #         VelbusFrame(
    #             address=self.address,
    #             message=message
    #         ),
    #         DaliDeviceSettings,
    #         # WARNING: this hangs the VMBDALI if the specified DALI-address
    #         #          is not responding. Only a module reset will resolve this.
    #         additional_check=lambda vbm: vbm.message.setting == DaliDeviceSettings.Setting.ActualLevel
    #     )
    #     return sanic.response.json(resp.message.setting_value.level)

    async def dimvalue_PUT(self,
                           path_info: str,
                           request: sanic.request,
                           bus: VelbusProtocol
                           ) -> sanic.response.HTTPResponse:
        """
        Set the dim value
        """
        try:
            resp = await self.e_dimvalue_PUT(
                path_info=path_info,
                request=request,
                bus=bus,
                allow_simulated_behaviour=False,
            )

            if resp.status == 202:
                # make this HTTP request synchroneous
                await self.delayed_calls[0].future
                resp.status = 200
            return resp
        except NonNative:
            return sanic.response.text('Bad Request: non-native request on native endpoint', 400)

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

        try:
            requested_status = DimStep.to_list(request.json)
        except TypeError as e:
            return sanic.response.text(f"Bad Request: {e}", 400)

        if len(requested_status) == 0:
            return sanic.response.text("Bad request: empty list", 400)
        if not allow_simulated_behaviour and not DimStep.is_trivial(requested_status):
            raise NonNative()

        try:
            self.delayed_calls = requested_status
        except ValueError as e:
            return sanic.response.text('Bad Request: could not parse PUT body: ' + str(e), 400)

        return sanic.response.text("OK", 202)
