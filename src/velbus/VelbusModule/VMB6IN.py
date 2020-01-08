from typing import Callable

import sanic.request
import sanic.response

from .NestedAddressVelbusModule import NestedAddressVelbusModule, VelbusModuleChannel
from ._registry import register

from ..VelbusMessage.ModuleInfo import ModuleInfo
from ..VelbusMessage.ModuleInfo.VMB6IN import VMB6IN as VMB6IN_MI
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from ..VelbusMessage.ModuleStatus import ModuleStatus6IN
from ..VelbusMessage.PushButtonStatus import PushButtonStatus

from ..VelbusProtocol import VelbusProtocol


@register(VMB6IN_MI)
class VMB6IN(NestedAddressVelbusModule):
    """
        VMB6IN module management

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
            channels=[1, 2, 3, 4, 5, 6], channel_type=VMB6INChannel,
        )


class VMB6INChannel(VelbusModuleChannel):
    def message(self, vbm: VelbusFrame):
        if isinstance(vbm.message, ModuleStatus6IN):
            self.state['input'] = vbm.message.input_status[8-self.channel]  # inputs are ordered LSb -> MSb

        elif isinstance(vbm.message, PushButtonStatus):
            push_button_status = vbm.message

            if push_button_status.just_pressed[8-self.channel]:  # inputs are ordered LSb -> MSb
                self.state['input'] = True

            if push_button_status.just_released[8-self.channel]:
                self.state['input'] = False

    async def _get_input_state(self, bus: VelbusProtocol):
        if 'input' not in self.state:
            _ = await bus.velbus_query(
                VelbusFrame(
                    address=self.address,
                    message=ModuleStatusRequest(
                        channel=0x3f,
                    ),
                ),
                ModuleStatus6IN,
            )
            # Do await the reply, but don't actually use it.
            # The reply will (also) be given to self.message(),
            # so by the time we get here, the cache will be up-to-date
            # may raise

        return self.state

    async def input_GET(self,
                        path_info: str,
                        request: sanic.request,
                        bus: VelbusProtocol
                        ) -> sanic.response.HTTPResponse:
        """
        Return the input status of the given input as a boolean.
        """
        del request  # unused

        if path_info != '':
            return sanic.response.text('Not found', status=404)

        status = await self._get_input_state(bus)

        return sanic.response.json(status['input'])
