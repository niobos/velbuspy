import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import UInt, Enum, Index, BlindNumber


@register
@attr.s(slots=True, auto_attribs=True)
class SwitchBlindV1(VelbusMessage):
    _priority: UInt(2) = 0

    class Command(Enum(8)):
        SwitchBlindUp = 0x05
        SwitchBlindDown = 0x06
    command: Command = Command.SwitchBlindUp

    channel: BlindNumber = 1

    timeout: UInt(24) = 0
    """
    timeout == 0 => default value
    timeout == 0xffffff => permanently on
    """


@register
@attr.s(slots=True, auto_attribs=True)
class SwitchBlindV2(VelbusMessage):
    _priority: UInt(2) = 0

    class Command(Enum(8)):
        SwitchBlindUp = 0x05
        SwitchBlindDown = 0x06
    command: Command = Command.SwitchBlindUp

    channel: Index(8, 2) = 1

    timeout: UInt(24) = 0
    """
    timeout == 0 => default value
    timeout == 0xffffff => permanently on
    """
