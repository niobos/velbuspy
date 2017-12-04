import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import Enum, UInt


@register
@attr.s(slots=True, auto_attribs=True)
class SensorTemperatureRequest(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        SensorTemperatureRequest = 0xe5
    _command: Command = Command.SensorTemperatureRequest

    class AutoSendInterval(UInt(8)):
        def to_json_able(self):
            if self == 0:
                return "no_change"
            elif self <= 4:  # and >= 1
                return "disabled"
            elif self <= 9:  # and >= 5
                return "on_temp_change"
            else:
                return self
    auto_send_interval: AutoSendInterval = 0
