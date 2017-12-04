import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import UInt, Enum, Index


@register
@attr.s(slots=True, auto_attribs=True)
class SetDimvalue(VelbusMessage):
    _priority: UInt(2) = 0

    class Command(Enum(8)):
        SetDimvalue = 0x07
    _command: Command = Command.SetDimvalue

    channel: Index(8, 4) = 1

    dimvalue: UInt(8) = 0

    dimspeed: UInt(16) = 0
