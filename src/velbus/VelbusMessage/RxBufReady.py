import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import UInt, Enum


@register
@attr.s(slots=True, auto_attribs=True)
class RxBufReady(VelbusMessage):
    _priority: UInt(2) = 0

    class Command(Enum(8)):
        RxBufReady = 0x0c
    _command: Command = Command.RxBufReady
