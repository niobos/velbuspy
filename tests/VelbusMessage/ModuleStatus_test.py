import pytest
import json

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleStatus import ModuleStatus8PBU, ModuleStatus6IN


def test_decode_8pbu():
    b = b'\x0f\xfb\x00\x07\xed\x00\x00\x00\x00\x00\x00\x02\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == ModuleStatus8PBU()

    assert json.dumps(a.to_json_able())


def test_data_8pbu():
    b = b'\x0f\xfb\x00\x07\xed\x01\x02\x04\x08\x10\xaa\x39\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == ModuleStatus8PBU(
        channel_pressed=[False, False, False, False, False, False, False, True],
        channel_enabled=[False, False, False, False, False, False, True, False],
        channel_not_inverted=[False, False, False, False, False, True, False, False],
        channel_locked=[False, False, False, False, True, False, False, False],
        channel_program_disabled=[False, False, False, True, False, False, False, False],

        prog_sunset_enabled=True,
        prog_sunrise_enabled=False,
        alarm2=ModuleStatus8PBU.LocalGlobal.Global,
        alarm2_enabled=False,
        alarm1=ModuleStatus8PBU.LocalGlobal.Global,
        alarm1_enabled=False,
        program=ModuleStatus8PBU.Program.Winter,
    )

    assert json.dumps(a.to_json_able())


def test_decode_6in():
    b = b'\x0f\xfb\x29\x05\xed\x00\x00\x00\x00\xdb\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == ModuleStatus6IN(
        input_status=[False, False, False, False, False, False, False, False],
        leds_slow_blink=[False, False, False, False, False, False, False, False],
        leds_fast_blink=[False, False, False, False, False, False, False, False],
    )

    assert json.dumps(a.to_json_able())
