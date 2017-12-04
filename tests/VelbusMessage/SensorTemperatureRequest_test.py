import pytest
import json

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.SensorTemperatureRequest import SensorTemperatureRequest


def test_decode():
    b = b'\x0f\xfb\x00\x02\xe5\x00\x0f\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == SensorTemperatureRequest()

    assert json.loads(json.dumps(a.message.to_json_able())) == {
        'type': 'SensorTemperatureRequest',
        'properties': {
            'auto_send_interval': 'no_change',
        }
    }


def test_autosend():
    b = b'\x0f\xfb\x00\x02\xe5\x01\x0e\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.message == SensorTemperatureRequest(auto_send_interval=1)
    assert a.message.to_json_able() == {
        'type': 'SensorTemperatureRequest',
        'properties': {
            'auto_send_interval': "disabled",
        }
    }
    assert SensorTemperatureRequest(auto_send_interval=6).to_json_able() == {
        'type': 'SensorTemperatureRequest',
        'properties': {
            'auto_send_interval': "on_temp_change",
        }
    }
    assert SensorTemperatureRequest(auto_send_interval=10).to_json_able() == {
        'type': 'SensorTemperatureRequest',
        'properties': {
            'auto_send_interval': 10,
        }
    }


def test_bounds():
    with pytest.raises(ValueError):
        a = SensorTemperatureRequest(auto_send_interval=256)
        a.validate()

    a = SensorTemperatureRequest()
    a.auto_send_interval = 256
    with pytest.raises(ValueError):
        a.validate()

    a.auto_send_interval = -1
    with pytest.raises(ValueError):
        a.validate()


