import json
from unittest.mock import Mock

import jsonpatch
import pytest

from velbus import HttpApi
from velbus.HttpApi import module_req
from velbus.VelbusProtocol import VelbusHttpProtocol
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
from velbus.VelbusMessage.ModuleType import ModuleType
from velbus.VelbusMessage.ModuleInfo.VMB2BLE import VMB2BLE as VMB2BLE_mi
from velbus.VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from velbus.VelbusMessage.BlindStatus import BlindStatusV2
from velbus.VelbusModule.VMBBLE import VMBBLE
from ..utils import make_awaitable


_ = VMBBLE  # dummy usage to force import
# import needed to auto-register the module for processing


@pytest.fixture(params=[1, 2])
def channel(request):
    return request.param


def VMB2BLE_module_info_exchange(module_address):
    return (
        VelbusFrame(
            address=module_address,
            message=ModuleTypeRequest(),
        ).to_bytes(),
        VelbusFrame(
            address=module_address,
            message=ModuleType(
                module_info=VMB2BLE_mi(),
            ),
        ).to_bytes()
    )


def VMB2BLE_module_status_exchange(module_address, channel, position):
    return (
        VelbusFrame(
            address=module_address,
            message=ModuleStatusRequest(
                channel=channel,
            )
        ).to_bytes(),
        VelbusFrame(
            address=module_address,
            message=BlindStatusV2(
                channel=channel,
                blind_status=BlindStatusV2.BlindStatus.Off,
                blind_position=position,
            ),
        ).to_bytes()
    )


@pytest.mark.asyncio
async def test_VMB2BLE_instantiation(generate_sanic_request, mock_velbus, module_address):
    mock_velbus.set_expected_conversation([
        VMB2BLE_module_info_exchange(module_address),
    ])

    req = generate_sanic_request()
    resp = await module_req(req, f"{module_address:02x}", '/type')
    mock_velbus.assert_conversation_happened_exactly()

    assert 200 == resp.status
    assert f"VMBBLE at 0x{module_address:02x}\r\n" == resp.body.decode('utf-8')


@pytest.mark.asyncio
async def test_VMB2BLE_status(generate_sanic_request, mock_velbus, module_address, channel):
    mock_velbus.set_expected_conversation([
        VMB2BLE_module_info_exchange(module_address),
        VMB2BLE_module_status_exchange(module_address, channel, 2),
    ])

    req = generate_sanic_request()
    resp = await module_req(req, f"{module_address:02x}", f"/{channel}/position")

    mock_velbus.assert_conversation_happened_exactly()

    assert 200 == resp.status
    assert '2' == resp.body.decode('utf-8')


@pytest.mark.asyncio
async def test_ws(generate_sanic_request, mock_velbus, module_address, channel):
    mock_velbus.set_expected_conversation([
        VMB2BLE_module_info_exchange(module_address),
        VMB2BLE_module_status_exchange(module_address, channel, 7),
    ])
    # Initialize the module
    sanic_req = generate_sanic_request()
    resp = await module_req(sanic_req, f"{module_address:02x}", f"/{channel}/position")
    assert 200 == resp.status

    client_state = dict()

    def receive(ops: str):
        patch = jsonpatch.JsonPatch(json.loads(ops))
        nonlocal client_state
        client_state = patch.apply(client_state)
        return make_awaitable(None)

    ws = Mock()
    ws.subscribed_modules = {module_address}
    ws.send = receive
    HttpApi.ws_clients.add(ws)

    sanic_req = generate_sanic_request()
    await HttpApi.ws_client_listen_module(VelbusHttpProtocol(sanic_req), module_address, ws)

    assert "off" == client_state[f"{module_address:02x}"][str(channel)]["status"]
    assert 7 == client_state[f"{module_address:02x}"][str(channel)]["position"]

    HttpApi.message(VelbusFrame(address=module_address, message=BlindStatusV2(
        channel=channel,
        blind_status=BlindStatusV2.BlindStatus.Up,
        blind_position=7,
    )))

    assert "up" == client_state[f"{module_address:02x}"][str(channel)]["status"]

    HttpApi.message(VelbusFrame(address=module_address, message=BlindStatusV2(
        channel=channel,
        blind_status=BlindStatusV2.BlindStatus.Off,
        blind_position=0,
    )))

    assert "off" == client_state[f"{module_address:02x}"][str(channel)]["status"]
    assert 0 == client_state[f"{module_address:02x}"][str(channel)]["position"]
