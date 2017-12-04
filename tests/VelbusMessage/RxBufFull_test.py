import json

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.RxBufFull import RxBufFull


def test_decode():
    b = b'\x0f\xf8\x00\x01\x0b\xed\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == RxBufFull()

    assert json.loads(json.dumps(a.message.to_json_able())) == {
        'type': 'RxBufFull',
        'properties': {}
    }
