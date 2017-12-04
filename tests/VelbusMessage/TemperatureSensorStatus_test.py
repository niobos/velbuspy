import pytest
import json

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.TemperatureSensorStatus import TemperatureSensorStatus


def test_decode():
    b = b'\x0f\xfb\x00\x08\xea\x00\x00\x00\x00\x00\x00\x00\x04\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == TemperatureSensorStatus()

    assert json.dumps(a.to_json_able())


def test_attributes():
    b = b'\x0f\xfb\x00\x08\xea\x01\x00\x00\x00\x00\x00\x00\x03\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b
    s = TemperatureSensorStatus(
        mode_push_button_locked=True,
    )
    assert a.message == s

    b = b'\x0f\xfb\x00\x08\xea\x00\x00\x00\x2b\x00\x00\x00\xd9\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b
    s = TemperatureSensorStatus(
        temperature=21.5,
    )
    assert a.message == s

    b = b'\x0f\xfb\x00\x08\xea\x00\x00\x00\x00\x00\x01\x23\xe0\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b
    s = TemperatureSensorStatus(
        sleep_timer=0x123,
    )
    assert a.message == s
    assert json.dumps(s.to_json_able())


def test_sleep_timer_names():
    s = TemperatureSensorStatus(
        sleep_timer=0xffff,
    )
    assert json.dumps(s.to_json_able())
