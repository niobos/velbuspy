import attr
from datetime import datetime

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import Enum, UInt


@register
@attr.s(slots=True, auto_attribs=True)
class RealTimeClockStatus(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        RealTimeClockStatus = 0xd8
    _command: Command = Command.RealTimeClockStatus

    class DayOfWeek(Enum(8)):
        Monday = 0
        Tuesday = 1
        Wednesday = 2
        Thursday = 3
        Friday = 4
        Saturday = 5
        Sunday = 6
    day_of_week: DayOfWeek = DayOfWeek.Monday

    hour: UInt(8) = 0
    minute: UInt(8) = 0

    def set_to(self, when=None):
        if when is None:
            when = datetime.now()
        self.day_of_week = when.weekday()
        self.hour = when.hour
        self.minute = when.minute
