import json
from unittest.mock import Mock

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

    ws = Mock()
    ws.subscribed_modules = {module_address}
    ws.send = Mock(return_value=make_awaitable(None))
    HttpApi.ws_clients.add(ws)

    sanic_req = generate_sanic_request()
    await HttpApi.ws_client_listen_module(VelbusHttpProtocol(sanic_req), module_address, ws)
    ws.send.assert_called_once()
    json_op = json.loads(ws.send.call_args[0][0])
    assert 1 == len(json_op)
    assert "add" == json_op[0]["op"]
    assert f"/{module_address:02x}" == json_op[0]["path"]
    assert isinstance(json_op[0]["value"], dict)
    assert 7 == json_op[0]["value"][str(channel)]["position"]
    ws.send.reset_mock()

    HttpApi.message(VelbusFrame(address=module_address, message=BlindStatusV2(
        channel=channel,
        blind_status=BlindStatusV2.BlindStatus.Up,
        blind_position=7,
    )))

    ws.send.assert_any_call(json.dumps([{
        "op": "add",
        "path": f"/{module_address:02x}/{channel}/status",
        "value": "up",
    }]))
    ws.send.reset_mock()

    HttpApi.message(VelbusFrame(address=module_address, message=BlindStatusV2(
        channel=channel,
        blind_status=BlindStatusV2.BlindStatus.Off,
        blind_position=0,
    )))

    ws.send.assert_any_call(json.dumps([{
        "op": "add",
        "path": f"/{module_address:02x}/{channel}/status",
        "value": "off",
    }]))
    ws.send.assert_any_call(json.dumps([{
        "op": "add",
        "path": f"/{module_address:02x}/{channel}/position",
        "value": 0,
    }]))
    ws.send.reset_mock()
