from .NestedAddressVelbusModule import NestedAddressVelbusModule, VelbusModuleChannel
from ._registry import register

from ..VelbusMessage.ModuleInfo.ModuleInfo import ModuleInfo
from ..VelbusMessage.ModuleInfo.VMBDALI import VMBDALI as VMBDALI_MI
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusProtocol import VelbusProtocol


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
            channels=[1, 2, 3, 4, 5, 6, 7, 8], channel_type=VMBDALIChannel,
        )


class VMBDALIChannel(VelbusModuleChannel):
    """
    VMBDALI channel

    state = {
    }
    """
    def message(self, vbm: VelbusFrame):
        # TODO: process relevant messages for state
        pass

    # TODO: add methods
