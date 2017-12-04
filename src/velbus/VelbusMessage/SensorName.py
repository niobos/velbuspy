import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import Enum, UInt, Bytes


@register
@attr.s(slots=True, auto_attribs=True)
class SensorName12(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        SensorName_part1 = 0xf0
        SensorName_part2 = 0xf1
    _command: Command = Command.SensorName_part1

    sensor_number: UInt(8) = 1

    sensor_name: Bytes(6) = b''


@register
@attr.s(slots=True, auto_attribs=True)
class SensorName3(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        SensorName_part3 = 0xf2
    _command: Command = Command.SensorName_part3

    sensor_number: UInt(8) = 1

    sensor_name: Bytes(4) = b''
