import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import UInt, Enum


@register
@attr.s(slots=True, auto_attribs=True)
class DaliDeviceSettingsRequest(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        COMMAND_TEMP_SENSOR_SETTINGS_REQUEST = 0xE7
    _command: Command = Command.COMMAND_TEMP_SENSOR_SETTINGS_REQUEST  # possible conflict!

    channel: UInt(8) = 1

    class Source(Enum(8)):
        Cache = 0
        Device = 1
    source: Source = 0
