import sanic.response

from .VelbusModule import VelbusModule


class UnknownModule(VelbusModule):
    def __init__(self, bus, address, update_state_cb, module_info):
        super().__init__(bus=bus,
                         address=address,
                         module_info=module_info)
        self.module_type = module_info.__class__.__name__

    def type_GET(self, path_info, request, bus):
        return sanic.response.text("{} at 0x{:02x} (not implemented)\r\n".format(
            self.module_type,
            self.address
        ))
