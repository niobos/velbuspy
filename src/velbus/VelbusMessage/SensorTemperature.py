import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import Enum, UInt, FixedPointSInt


@register
@attr.s(slots=True, auto_attribs=True)
class SensorTemperature(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        SensorTemperature = 0xe6
    _command: Command = Command.SensorTemperature

    current_temperature: FixedPointSInt(7, 9) = 0
    minimum_temperature: FixedPointSInt(7, 9) = 0
    maximum_temperature: FixedPointSInt(7, 9) = 0


@register
@attr.s(slots=True, auto_attribs=True)
class SensorTemperatureShort(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        SensorTemperature = 0xe6
    _command: Command = Command.SensorTemperature

    current_temperature: FixedPointSInt(7, 1) = 0
    minimum_temperature: FixedPointSInt(7, 1) = 0
    maximum_temperature: FixedPointSInt(7, 1) = 0
