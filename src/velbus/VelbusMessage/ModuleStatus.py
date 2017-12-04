import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import Enum, UInt, Bitmap, Bool


@register
@attr.s(slots=True, auto_attribs=True)
class ModuleStatus(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        ModuleStatus = 0xed
    _command: Command = Command.ModuleStatus

    channel_pressed: Bitmap(8) = Bitmap(8).zero()
    channel_enabled: Bitmap(8) = Bitmap(8).zero()
    channel_not_inverted: Bitmap(8) = Bitmap(8).zero()
    channel_locked: Bitmap(8) = Bitmap(8).zero()
    channel_program_disabled: Bitmap(8) = Bitmap(8).zero()

    # byte 7
    prog_sunset_enabled: Bool = False
    prog_sunrise_enabled: Bool = False

    class LocalGlobal(Enum(1)):
        Local = 0
        Global = 1
    alarm2: LocalGlobal = LocalGlobal.Local
    alarm2_enabled: Bool = False
    alarm1: LocalGlobal = LocalGlobal.Local
    alarm1_enabled: Bool = False

    class Program(Enum(2)):
        No = 0
        Summer = 1
        Winter = 2
        Holiday = 3
    program: Program = Program.No
