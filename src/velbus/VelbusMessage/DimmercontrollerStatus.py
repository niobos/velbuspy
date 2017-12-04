import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import UInt, Enum, Index, DisableInhibitForced, LedStatus


@register
@attr.s(slots=True, auto_attribs=True)
class DimmercontrollerStatus(VelbusMessage):
    _priority: UInt(2) = 0

    class Command(Enum(8)):
        DimmercontrollerStatus = 0xb8
    _command: Command = Command.DimmercontrollerStatus

    channel: Index(8, 4) = 1

    disable_inhibit_force: DisableInhibitForced = DisableInhibitForced.Normal

    dimvalue: UInt(8) = 0

    led_status: LedStatus = LedStatus.Off

    delay_time: UInt(24) = 0
