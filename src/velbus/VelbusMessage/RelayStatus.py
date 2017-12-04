import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import Enum, UInt, Index, DisableInhibitForced, LedStatus


@register
@attr.s(slots=True, auto_attribs=True)
class RelayStatus(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        RelayStatus = 0xfb
    _command: Command = Command.RelayStatus

    relay: Index(8) = 1

    disable_inhibit_force: DisableInhibitForced = DisableInhibitForced.Normal

    class RelayStatus(Enum(8)):
        Off = 0
        On = 1
        IntervalTimer = 3
    relay_status: RelayStatus = RelayStatus.Off

    led_status: LedStatus = LedStatus.Off

    delay_timer: UInt(24) = 0
