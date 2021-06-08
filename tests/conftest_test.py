import logging

import pytest

from velbus.VelbusProtocol import VelbusProtocol
from velbus.VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from velbus.VelbusMessage.VelbusFrame import VelbusFrame


def test_module_address(module_address):
    assert 0 <= module_address <= 0xff


def test_debug_logging(debug_logging):
    logging.getLogger(__name__).debug('test')


@pytest.mark.asyncio
async def test_mock_velbus(mock_velbus, module_address):
    mock_velbus.set_expected_conversation([
        (
            VelbusFrame(
                address=module_address,
                message=ModuleStatusRequest(),
            ).to_bytes(),
            VelbusFrame(
                address=0,
                message=ModuleStatusRequest(),
            ).to_bytes(),
        )
    ])

    bus = VelbusProtocol(client_id="test")
    coro = bus.velbus_query(
        VelbusFrame(address=module_address, message=ModuleStatusRequest()),
        ModuleStatusRequest,
    )
    ret = await coro

    mock_velbus.assert_conversation_happened_exactly()
