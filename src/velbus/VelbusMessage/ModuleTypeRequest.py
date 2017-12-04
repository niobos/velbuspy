import attr

from .VelbusMessage import VelbusMessage
from ._types import Bool, UInt


@attr.s(slots=True, auto_attribs=True)
class ModuleTypeRequest(VelbusMessage):
    _priority: UInt(2) = 3
    _remote_transmit_request: Bool = True

    def data(self):
        return b''
