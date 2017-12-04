import json
import pytest
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.UnknownMessage import UnknownMessage


def test_decode_unknown():
    b = b'\x0f\xf8\x00\x01\x01\xf7\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.message == UnknownMessage(priority=0, data=b'\x01')
    assert a.to_bytes() == b

    assert json.loads(json.dumps(a.to_json_able())) == {
        'address': 0,
        'message': {
            'type': 'UnknownMessage',
            'properties': {},
        }
    }

def test_decode_rtr():
    b = b'\x0f\xfb\x00\x40\xb6\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.message == ModuleTypeRequest()
    assert a.to_bytes() == b

    assert json.loads(json.dumps(a.to_json_able())) == {
        'address': 0,
        'message': {
            'type': 'ModuleTypeRequest',
            'properties': {},
        }
    }

def test_decode_too_long():
    b = b'\x0f\xf8\x00\x02\x0a\x00\xed\x04'  # BusActive, but too long
    a = VelbusFrame.from_bytes(b)
    assert a.message == UnknownMessage(priority=0, data=b'\x0a\x00')
    assert a.to_bytes() == b

    assert json.dumps(a.to_json_able())

def test_decode_too_short():
    b = b'\x0f\xf8\x00\x07\xea\x00\x00\x00\x00\x00\x00\x08\x04'  # SensorTemperature, but too short
    a = VelbusFrame.from_bytes(b)
    assert a.message == UnknownMessage(priority=0, data=b'\xea\x00\x00\x00\x00\x00\x00')
    assert a.to_bytes() == b

    assert json.dumps(a.to_json_able())

def test_decode_invalid():
    with pytest.raises(BufferError):
        VelbusFrame.from_bytes(b'')  # <6 bytes
    with pytest.raises(ValueError):
        VelbusFrame.from_bytes(b'\x00\x00\x00\x00\x00\x00')  # invalid header
    with pytest.raises(ValueError):
        VelbusFrame.from_bytes(b'\x0f\x00\x00\x00\x00\x00')  # invalid header
    with pytest.raises(ValueError):
        VelbusFrame.from_bytes(b'\x0f\xf8\x00\xff\x00\x00')  # invalid header
    with pytest.raises(BufferError):
        VelbusFrame.from_bytes(b'\x0f\xf8\x00\x0f\x00\x00')  # not enough data bytes
    with pytest.raises(ValueError):
        VelbusFrame.from_bytes(b'\x0f\xf8\x00\x00\x00\x00')  # invalid checksum
    with pytest.raises(ValueError):
        VelbusFrame.from_bytes(b'\x0f\xf8\x00\x00\xf9\x00')  # invalid EOF

