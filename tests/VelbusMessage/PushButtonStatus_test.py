import pytest
import json

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.PushButtonStatus import PushButtonStatus


def test_decode():
    b = b'\x0f\xf8\x00\x04\x00\x00\x00\x00\xf5\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == PushButtonStatus()

    assert json.dumps(a.to_json_able())

def test_pressed():
    b = b'\x0f\xf8\x00\x04\x00\x01\x0a\x00\xea\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.message == PushButtonStatus(
        just_pressed=[False, False, False, False, False, False, False, True],
        just_released=[False, False, False, False, True, False, True, False],
    )
    assert a.to_bytes() == b

