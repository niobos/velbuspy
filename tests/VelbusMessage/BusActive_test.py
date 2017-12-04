import json

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.BusActive import BusActive


def test_decode():
    b = b'\x0f\xf8\x00\x01\x0a\xee\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == BusActive()

    assert json.loads(json.dumps(a.message.to_json_able())) == {
        'type': 'BusActive',
        'properties': {}
    }
