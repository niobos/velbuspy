import pytest
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
import json

def test_decode():
    b = b'\x0f\xfb\x01\x40\xb5\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a == VelbusFrame(address=1, message=ModuleTypeRequest())

    assert json.loads(json.dumps(a.message.to_json_able())) == {
        'type': 'ModuleTypeRequest',
        'properties': {}
    }

def test_decode_wrong_rtr():
    b = b'\x0f\xfb\x01\x00\xf5\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message != ModuleTypeRequest()
