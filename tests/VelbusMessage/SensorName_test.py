import pytest
import json

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.SensorName import SensorName12, SensorName3
from velbus.VelbusMessage.UnknownMessage import UnknownMessage

def test_decode():
    b = b'\x0f\xfb\x00\x08\xf0\x01ABCDEF\x68\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == SensorName12(
        command=SensorName12.Command.SensorName_part1,
        sensor_name=b'ABCDEF',
    )

    assert json.loads(json.dumps(a.message.to_json_able())) == {
        'type': 'SensorName12',
        'properties': {
            'sensor_number': 1,
            'sensor_name': 'ABCDEF',
        }
    }


def test_decode3():
    b = b'\x0f\xfb\x00\x06\xf2\x01ABCD\xf3\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == SensorName3(
        command=SensorName3.Command.SensorName_part3,
        sensor_name=b'ABCD',
    )

    assert json.dumps(a.message.to_json_able())


def test_decode3_full_length():
    b = b'\x0f\xfb\x00\x08\xf2\x01ABCDEF\x66\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b
    assert isinstance(a.message, UnknownMessage)
