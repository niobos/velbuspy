import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import Enum, UInt, Bitmap


@register
@attr.s(slots=True, auto_attribs=True)
class PushButtonStatus(VelbusMessage):
    _priority: UInt(2) = 0

    class Command(Enum(8)):
        PushButtonStatus = 0x00
    _command: Command = Command.PushButtonStatus

    just_pressed: Bitmap(8) = Bitmap(8).zero()
    just_released: Bitmap(8) = Bitmap(8).zero()
    long_pressed: Bitmap(8) = Bitmap(8).zero()
