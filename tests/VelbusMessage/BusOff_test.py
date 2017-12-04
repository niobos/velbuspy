import pytest
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.BusOff import BusOff
import json

def test_decode():
    b = b'\x0f\xf8\x00\x01\x09\xef\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == BusOff()

    assert json.loads(json.dumps(a.message.to_json_able())) == {
        'type': 'BusOff',
        'properties': {}
    }

def test_command():
    a = BusOff()
    a._command = 9
    a.validate()

    a._command = 1
    with pytest.raises(ValueError):
        a.validate()
