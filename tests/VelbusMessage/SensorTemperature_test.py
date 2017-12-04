import json

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.SensorTemperature import SensorTemperature, SensorTemperatureShort


def test_decode():
    b = b'\x0f\xfb\x00\x07\xe6\x00\x20\xfe\x00\x02\x00\xe9\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == SensorTemperature(
        current_temperature=0.0625,
        minimum_temperature=-1.0,
        maximum_temperature=1.0,
    )

    assert json.loads(json.dumps(a.message.to_json_able())) == {
        'type': 'SensorTemperature',
        'properties': {
            'current_temperature': 0.0625,
            'minimum_temperature': -1.0,
            'maximum_temperature': 1.0,
        }
    }


def test_decode_short():
    b = b'\x0f\xfb\x00\x04\xe6\x01\xfe\x02\x0b\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == SensorTemperatureShort(
        current_temperature=0.5,
        minimum_temperature=-1.0,
        maximum_temperature=1.0,
    )

    assert json.dumps(a.to_json_able())
