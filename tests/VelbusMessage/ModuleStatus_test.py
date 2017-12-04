import pytest
import json

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleStatus import ModuleStatus

def test_decode():
    b = b'\x0f\xfb\x00\x07\xed\x00\x00\x00\x00\x00\x00\x02\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == ModuleStatus()

    assert json.dumps(a.to_json_able())

def test_data():
    b = b'\x0f\xfb\x00\x07\xed\x01\x02\x04\x08\x10\xaa\x39\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == ModuleStatus(
        channel_pressed=[False, False, False, False, False, False, False, True],
        channel_enabled=[False, False, False, False, False, False, True, False],
        channel_not_inverted=[False, False, False, False, False, True, False, False],
        channel_locked=[False, False, False, False, True, False, False, False],
        channel_program_disabled=[False, False, False, True, False, False, False, False],

        prog_sunset_enabled=True,
        prog_sunrise_enabled=False,
        alarm2=ModuleStatus.LocalGlobal.Global,
        alarm2_enabled=False,
        alarm1=ModuleStatus.LocalGlobal.Global,
        alarm1_enabled=False,
        program=ModuleStatus.Program.Winter,
    )

    assert json.dumps(a.to_json_able())
