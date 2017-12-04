import pytest
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.InterfaceStatusRequest import InterfaceStatusRequest
import json

def test_decode():
    b = b'\x0f\xf8\x00\x01\x0e\xea\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == InterfaceStatusRequest()

    assert json.loads(json.dumps(a.message.to_json_able())) == {
        'type': 'InterfaceStatusRequest',
        'properties': {}
    }
