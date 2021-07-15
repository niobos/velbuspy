from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.DaliDeviceSettings import DaliDeviceSettings, DaliDeviceSettingValueLevel


def test_decode():
    b = b'\x0f\xfb\xda\x04\xe8\01\x1a\xfe\x17\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert isinstance(a.message, DaliDeviceSettings)
    assert a.message.setting == DaliDeviceSettings.Setting.ActualLevel
    assert isinstance(a.message.setting_value, DaliDeviceSettingValueLevel)
    assert a.message.setting_value.level == 254
