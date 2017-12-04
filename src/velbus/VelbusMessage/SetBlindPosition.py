import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import UInt, Enum, Index


@register
@attr.s(slots=True, auto_attribs=True)
class SetBlindPosition(VelbusMessage):
    _priority: UInt(2) = 0

    class Command(Enum(8)):
        SetBlindPosition = 0x1c
    _command: Command = Command.SetBlindPosition

    channel: Index(8, 2) = 1

    position: UInt(8) = 0
