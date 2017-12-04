import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import Enum, UInt


@register
@attr.s(slots=True, auto_attribs=True)
class ModuleStatusRequest(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        ModuleStatusRequest = 0xfa

    _command: Command = Command.ModuleStatusRequest
    channel: UInt(8) = 0
