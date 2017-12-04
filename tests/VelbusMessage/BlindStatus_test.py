import json

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.BlindStatus import BlindStatusV1, BlindStatusV2
from velbus.VelbusMessage._types import BlindTimeout


def test_decode_v1():
    b = b'\x0f\xfb\x2b\x08\xec\x0c\x01\x00\x00\x00\x00\x00\xca\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == BlindStatusV1(
        channel=2,
        default_timeout=BlindTimeout.t30sec,
        led_status=BlindStatusV1.LedStatus.Off,
    )

    assert json.loads(json.dumps(a.message.to_json_able())) == {
        'type': 'BlindStatusV1',
        'properties': {
            'channel': 2,
            'blind_status': {'name': 'Off', 'value': 0},
            'default_timeout': {'name': 't30sec', 'value': 1},
            'led_status': {'name': 'Off', 'value': 0},
            'delay_time': 0,
        }
    }


def test_decode_v2():
    b = b'\x0f\xfb\x2a\x08\xec\x01\x1e\x00\x08\x00\x00\x00\xb1\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == BlindStatusV2(
        default_timeout=30,
        led_status=BlindStatusV2.LedStatus.UpOn
    )

    assert json.loads(json.dumps(a.message.to_json_able())) == {
        'type': 'BlindStatusV2',
        'properties': {
            'alarm1_locality': {'name': 'Local', 'value': 0},
            'alarm1_on': 0,
            'alarm2_locality': {'name': 'Local', 'value': 0},
            'alarm2_on': 0,
            'auto_mode': {'name': 'Disabled', 'value': 0},
            'blind_position': 0,
            'blind_status': {'name': 'Off', 'value': 0},
            'channel': 1,
            'default_timeout': 30,
            'led_status': {'name': 'UpOn', 'value': 8},
            'locked_inhibited_forced': {'name': 'Normal', 'value': 0},
            'sunrise_enabled': 0,
            'sunset_enabled': 0,
        }
    }
