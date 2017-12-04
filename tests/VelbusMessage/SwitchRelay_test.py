import pytest
import json

from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.SwitchRelay import SwitchRelay


@pytest.fixture(
    scope='function',
    params=[
        (
            b'\x0f\xf8\x00\x02\x01\x01\xf5\x04',
            SwitchRelay(
                command=SwitchRelay.Command.SwitchRelayOff
            ),
            {
                'type': 'SwitchRelay',
                'properties': {
                    'command': {'name': 'SwitchRelayOff', 'value': 1},
                    'relay': 1,
                }
            },
        ),
        (
            b'\x0f\xf8\x00\x02\x02\x04\xf1\x04',
            SwitchRelay(
                command=SwitchRelay.Command.SwitchRelayOn,
                relay=3,
            ),
            {
                'type': 'SwitchRelay',
                'properties': {
                    'command': {'name': 'SwitchRelayOn', 'value': 2},
                    'relay': 3,
                }
            },
        ),
    ])
def message(request):
    yield request.param


def test_message(message):
    b = message[0]
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b
    assert a.message == message[1]
    assert json.loads(json.dumps(a.message.to_json_able())) == message[2]
