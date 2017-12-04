import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import Enum, UInt, Index


@register
@attr.s(slots=True, auto_attribs=True)
class SwitchRelay(VelbusMessage):
    _priority: UInt(2) = 0

    class Command(Enum(8)):
        SwitchRelayOff = 0x01
        SwitchRelayOn = 0x02
    command: Command = Command.SwitchRelayOff

    relay: Index(8) = 1
