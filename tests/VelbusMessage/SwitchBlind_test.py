import json

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.SwitchBlind import SwitchBlindV1


def test_decode_v1():
    b = b'\x0f\xf8\x2b\x05\x05\x03\x00\x00\x00\xc1\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == SwitchBlindV1(
        command=SwitchBlindV1.Command.SwitchBlindUp,
        channel=1,
    )

    assert json.dumps(a.message.to_json_able())
