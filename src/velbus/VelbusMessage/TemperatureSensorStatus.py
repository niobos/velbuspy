import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import Enum, UInt, Bool, FixedPointSInt


@register
@attr.s(slots=True, auto_attribs=True)
class TemperatureSensorStatus(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        TemperatureSensorStatus = 0xea
    _command: Command = Command.TemperatureSensorStatus

    # byte2
    class HeaterCooler(Enum(1)):
        Heater = 0
        Cooler = 1
    heater_cooler: HeaterCooler = HeaterCooler.Heater

    class TemperatureMode(Enum(3)):
        Safe = 0
        Night = 1
        Day = 2
        Comfort = 4
    temperature_mode: TemperatureMode = TemperatureMode.Safe

    auto_send_temperature_enabled: Bool = False

    class TimerMode(Enum(2)):
        Run = 0
        Manual = 1
        SleepTimer = 2
        Disabled = 3
    timer_mode: TimerMode = TimerMode.Run

    mode_push_button_locked: Bool = False

    # byte3
    all_room_program_present: Bool = False

    class ProgramStepReceived(Enum(3)):
        Safe = 0
        Night = 1
        Day = 2
        Comfort = 4
    program_step_received: ProgramStepReceived = ProgramStepReceived.Safe

    zone_program_present: Bool = False

    sensor_program_present: Bool = False

    valve_unjamming_enabled: Bool = False

    pump_unjamming_enabled: Bool = False

    # byte4
    _reserved_0: Bool = False
    high_alarm: Bool = False
    low_alarm: Bool = False
    heater: Bool = False
    cooler: Bool = False
    comfort_or_day: Bool = False
    boost: Bool = False
    pump: Bool = False

    # byte5
    temperature: FixedPointSInt(7, 1) = 0
    # A more detailed temperature is available in SensorTemperature

    # byte6
    set_temperature: FixedPointSInt(7, 1) = 0

    class SleepTimer(UInt(16)):
        def to_json_able(self):
            if self == 0:
                return 'inactive'
            elif self == 0xffff:
                return 'manual'
            else:
                return self
    sleep_timer: SleepTimer = SleepTimer(0)
