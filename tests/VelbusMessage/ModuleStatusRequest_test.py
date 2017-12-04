import pytest
import json

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleStatusRequest import ModuleStatusRequest

def test_decode():
    b = b'\x0f\xfb\x00\x02\xfa\x00\xfa\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == ModuleStatusRequest()

    assert json.dumps(a.to_json_able())

def test_dontcare():
    b = b'\x0f\xfb\x00\x02\xfa\x4e\xac\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.message == ModuleStatusRequest(
        channel=0x4e,
    )
    assert a.to_bytes() == b
    assert json.dumps(a.to_json_able())
