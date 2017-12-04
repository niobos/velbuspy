import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import Enum, UInt, Index


@register
@attr.s(slots=True, auto_attribs=True)
class ManageLed(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        ClearLed = 0xf5
        SetLed = 0xf6
        SlowlyBlinkLed = 0xf7
        FastBlinkLed = 0xf8
        VeryFastBlinkLed = 0xf9
    command: Command = Command.ClearLed

    led: Index(8) = 1
