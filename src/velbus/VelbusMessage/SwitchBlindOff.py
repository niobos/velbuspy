import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import UInt, Enum, Index, BlindNumber


@register
@attr.s(slots=True, auto_attribs=True)
class SwitchBlindOffV1(VelbusMessage):
    _priority: UInt(2) = 0

    class Command(Enum(8)):
        SwitchBlindOff = 0x04
    _command: Command = Command.SwitchBlindOff

    channel: BlindNumber = 1


@register
@attr.s(slots=True, auto_attribs=True)
class SwitchBlindOffV2(VelbusMessage):
    _priority: UInt(2) = 0

    class Command(Enum(8)):
        SwitchBlindOff = 0x04
    _command: Command = Command.SwitchBlindOff

    channel: Index(8, 2) = 1
