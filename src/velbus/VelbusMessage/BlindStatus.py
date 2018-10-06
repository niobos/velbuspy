import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import UInt, Enum, Index, Bool, BlindNumber, BlindTimeout


# Two possible decodes for BlindStatus message 0xEC
# they can be identified by the `channel` field:
# The old modules send either {0b00000011, 0b00001100}
# The nem modules s end either {0b00000001, 0b00000010}
#
# Both decodes will be tried, the "wrong" one will always raise ValueError()


@register
@attr.s(slots=True, auto_attribs=True)
class BlindStatusV1(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        BlindStatus = 0xec
    _command: Command = Command.BlindStatus

    channel: BlindNumber = 1

    _reserved: UInt(6) = 0
    default_timeout: BlindTimeout = BlindTimeout.t30sec

    class BlindStatus(Enum(8)):
        Off = 0
        Blind1Up = 1
        Blind1Down = 2
        Blind2Up = 4
        Blind2Down = 8
    blind_status: BlindStatus = BlindStatus.Off

    class LedStatus(Enum(8)):
        Off = 0x00
        DownOn = 0x80
        DownSlowBlink = 0x40
        DownFastBlink = 0x20
        DownVeryFastBlink = 0x10
        UpOn = 0x08
        UpSlowBlink = 0x04
        UpFastBlink = 0x02
        UpVeryFastBlink = 0x01
    led_status: LedStatus = LedStatus.Off

    delay_time: UInt(24) = 0


@register
@attr.s(slots=True, auto_attribs=True)
class BlindStatusV2(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        BlindStatus = 0xec
    _command: Command = Command.BlindStatus

    channel: Index(8, 2) = 1

    default_timeout: UInt(8) = 0

    class BlindStatus(Enum(8)):
        Off = 0
        Up = 1
        Down = 2
    blind_status: BlindStatus = BlindStatus.Off

    class LedStatus(Enum(8)):
        Off = 0x00
        DownOn = 0x80
        DownSlowBlink = 0x40
        DownFastBlink = 0x20
        DownVeryFastBlink = 0x10
        UpOn = 0x08
        UpSlowBlink = 0x04
        UpFastBlink = 0x02
        UpVeryFastBlink = 0x01
    led_status: LedStatus = LedStatus.Off

    blind_position: UInt(8) = 0

    class LockedInhibitedForced(Enum(8)):
        Normal = 0
        Inhibted = 1
        InhibitPresetDown = 2
        InhibitPresetUp = 3
        ForcedDown = 4
        ForcedUp = 5
        Locked = 6
    locked_inhibited_forced: LockedInhibitedForced = LockedInhibitedForced.Normal

    class LocalGlobal(Enum(1)):
        Local = 0
        Global = 1
    class AutoMode(Enum(2)):
        Disabled = 0
        Mode1 = 1
        Mode2 = 2
        Mode3 = 3
    sunset_enabled: Bool = False
    sunrise_enabled: Bool = False
    alarm2_locality: LocalGlobal = LocalGlobal.Local
    alarm2_on: Bool = False
    alarm1_locality: LocalGlobal = LocalGlobal.Local
    alarm1_on: Bool = False
    auto_mode: AutoMode = AutoMode.Disabled
