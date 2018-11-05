import pytest

from velbus.HttpApi import module_req
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
from velbus.VelbusMessage.ModuleType import ModuleType
from velbus.VelbusMessage.ModuleInfo.VMB2BLE import VMB2BLE as VMB2BLE_mi
from velbus.VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from velbus.VelbusMessage.BlindStatus import BlindStatusV2
from velbus.VelbusModule.VMBBLE import VMBBLE


_ = VMBBLE  # dummy usage to force import
# import needed to auto-register the module for processing


@pytest.mark.asyncio
async def test_VMB2BLE_instantiation(generate_sanic_request, mock_velbus):
    mock_velbus.set_expected_conversation([
        (
            VelbusFrame(
                address=0x11,
                message=ModuleTypeRequest(),
            ).to_bytes(),
            VelbusFrame(
                address=0x11,
                message=ModuleType(
                    module_info=VMB2BLE_mi(),
                ),
            ).to_bytes()
        ),
    ])

    req = generate_sanic_request()
    resp = await module_req(req, '11', '/type')
    mock_velbus.assert_conversation_happened_exactly()

    assert 200 == resp.status
    assert 'VMBBLE at 0x11\r\n' == resp.body.decode('utf-8')


@pytest.mark.asyncio
async def test_VMB2BLE_status(generate_sanic_request, mock_velbus):
    mock_velbus.set_expected_conversation([
        (
            VelbusFrame(
                address=0x11,
                message=ModuleTypeRequest(),
            ).to_bytes(),
            VelbusFrame(
                address=0x11,
                message=ModuleType(
                    module_info=VMB2BLE_mi(),
                ),
            ).to_bytes()
        ),
        (
            VelbusFrame(
                address=0x11,
                message=ModuleStatusRequest(
                    channel=1
                )
            ).to_bytes(),
            VelbusFrame(
                address=0x11,
                message=BlindStatusV2(
                    channel=1,
                    blind_status=BlindStatusV2.BlindStatus.Off,
                    blind_position=2,
                ),
            ).to_bytes()
        ),
    ])

    req = generate_sanic_request()
    resp = await module_req(req, '11', '/1/position')

    mock_velbus.assert_conversation_happened_exactly()

    assert 200 == resp.status
    assert '2' == resp.body.decode('utf-8')
