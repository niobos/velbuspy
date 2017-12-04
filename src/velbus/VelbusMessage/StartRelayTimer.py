import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import Enum, UInt, Index


@register
@attr.s(slots=True, auto_attribs=True)
class StartRelayTimer(VelbusMessage):
    _priority: UInt(2) = 0

    class Command(Enum(8)):
        StartRelayTimer = 0x03
    command: Command = Command.StartRelayTimer

    relay: Index(8) = 1

    delay_time: UInt(24) = 0
    """
    Special cases:
    delay_time == 0: delay_time taken from the hex switches
        if hex_switches are set to momentary => No action
        if hex_switches are set to toggle => Switch on permanently
    delay_time == 0xffffff: switch on permanently
    """
