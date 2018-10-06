import sanic.request
import sanic.response

from .NestedAddressVelbusModule import NestedAddressVelbusModule
from ._registry import register

from ..VelbusMessage.ModuleInfo.VMB6IN import VMB6IN as VMB6IN_MI
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from ..VelbusMessage.ModuleStatus import ModuleStatus6IN
from ..VelbusMessage.PushButtonStatus import PushButtonStatus

from ..VelbusProtocol import VelbusProtocol


@register(VMB6IN_MI)
class VMB6IN(NestedAddressVelbusModule):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addresses = [1, 2, 3, 4, 5, 6]

    def message(self, vbm: VelbusFrame):
        if isinstance(vbm.message, ModuleStatus6IN):
            for i in range(1, 6+1):
                self.state[str(i)]['input'] = vbm.message.input_status[8-i]  # inputs are ordered LSb -> MSb

        elif isinstance(vbm.message, PushButtonStatus):
            push_button_status = vbm.message

            for input_num in range(1, 6+1):  # 6 channels
                if push_button_status.just_pressed[8-input_num]:  # inputs are ordered LSb -> MSb
                    self.state[str(input_num)]['input'] = True

                if push_button_status.just_released[8-input_num]:
                    self.state[str(input_num)]['input'] = False

    async def _get_input_state(self, bus: VelbusProtocol, input_num: int):
        if str(input_num) not in self.state:
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

        return self.state[str(input_num)]

    async def input_GET(self,
                        subaddress: int,
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

        status = await self._get_input_state(bus, subaddress)

        return sanic.response.json(status['input'])
