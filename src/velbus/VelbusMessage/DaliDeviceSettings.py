import attr

from ._registry import register
from ._utils import AttrSerializer
from .VelbusMessage import VelbusMessage
from ._types import UInt, Enum


@attr.s(slots=True)
class DaliDeviceSettingValue(AttrSerializer):
    pass


@attr.s(slots=True, auto_attribs=True)
class DaliDeviceSettingValueLevel(DaliDeviceSettingValue):
    level: UInt(8) = 255


@register
@attr.s(slots=True, auto_attribs=True)
class DaliDeviceSettings(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        COMMAND_TEMP_SENSOR_SETTINGS_P1 = 0xE8
    _command: Command = Command.COMMAND_TEMP_SENSOR_SETTINGS_P1  # possible conflict!

    channel: UInt(8) = 1

    class Setting(Enum(8)):
        SceneS0Level = (0, DaliDeviceSettingValueLevel)
        SceneS1Level = (1, DaliDeviceSettingValueLevel)
        SceneS2Level = (2, DaliDeviceSettingValueLevel)
        SceneS3Level = (3, DaliDeviceSettingValueLevel)
        SceneS4Level = (4, DaliDeviceSettingValueLevel)
        SceneS5Level = (5, DaliDeviceSettingValueLevel)
        SceneS6Level = (6, DaliDeviceSettingValueLevel)
        SceneS7Level = (7, DaliDeviceSettingValueLevel)
        SceneS8Level = (8, DaliDeviceSettingValueLevel)
        SceneS9Level = (9, DaliDeviceSettingValueLevel)
        SceneS10Level = (10, DaliDeviceSettingValueLevel)
        SceneS11Level = (11, DaliDeviceSettingValueLevel)
        SceneS12Level = (12, DaliDeviceSettingValueLevel)
        SceneS13Level = (13, DaliDeviceSettingValueLevel)
        SceneS14Level = (14, DaliDeviceSettingValueLevel)
        SceneS15Level = (15, DaliDeviceSettingValueLevel)
        PowerOnLevel = (16, DaliDeviceSettingValueLevel)
        SystemFailureLevel = (17, DaliDeviceSettingValueLevel)
        MinimumLevel = (18, DaliDeviceSettingValueLevel)
        MaximumLevel = (19, DaliDeviceSettingValueLevel)
        FadeTimeRate = (20, None)
        GroupMembership0_15 = (21, None)
        GroupNMembershipA0_31 = (22, None)
        GroupNMembershipA32_63 = (23, None)
        # 24 unused
        DeviceType = (25, None)
        ActualLevel = (26, DaliDeviceSettingValueLevel)

        def __new__(cls, value, decoder):
            obj = object.__new__(cls)
            obj._value_ = value
            obj.decoder = decoder
            return obj
    setting: Setting = Setting.ActualLevel

    setting_value: DaliDeviceSettingValue = None

    @classmethod
    def from_bytes(cls, priority, remote_transmit_request, data) -> "DaliDeviceSettings":
        if len(data) < 4:
            raise ValueError("Message not long enough")

        obj = cls.__new__(cls)
        obj._priority = priority
        obj._remote_transmit_request = remote_transmit_request
        obj._command = DaliDeviceSettings.Command(data[0])  # may raise
        obj.channel = data[1]
        obj.setting = DaliDeviceSettings.Setting.from_int(data[2])  # may raise
        if obj.setting.decoder is None:
            raise ValueError('unknown decoder')
        obj.setting_value = obj.setting.decoder.from_bytes(data[3:])  # may raise

        return obj

    def data(self) -> bytes:
        return bytes([self._command.value, self.channel, self.setting.value]) + self.setting_value.data()
