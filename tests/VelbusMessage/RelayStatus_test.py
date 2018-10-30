import pytest
import json

from velbus.VelbusMessage._types import LedStatus
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.RelayStatus import RelayStatus


@pytest.mark.parametrize('binary,frame,json', [
    (
        b'\x0f\xfb\x20\x08\xfb\x02\x00\x01\x80\x00\x00\x00\x50\x04',
        VelbusFrame(
            address=0x20,
            message=RelayStatus(
                channel=2,
                relay_status=RelayStatus.RelayStatus.On,
                led_status=LedStatus.On,
            ),
        ),
        None
    ),
])
def test_message(binary: bytes, frame: VelbusFrame, json: dict):
    b = binary
    a = VelbusFrame.from_bytes(b)

    # test roundtrip
    assert a.to_bytes() == b

    # test decode
    assert a == frame

    # test JSON
    if json is not None:
        assert json.loads(json.dumps(a.message.to_json_able())) == json

