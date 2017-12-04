import json

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.RxBufReady import RxBufReady


def test_decode():
    b = b'\x0f\xf8\x00\x01\x0c\xec\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == RxBufReady()

    assert json.loads(json.dumps(a.message.to_json_able())) == {
        'type': 'RxBufReady',
        'properties': {}
    }
