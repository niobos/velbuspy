import pytest

from velbus import HttpApi
from velbus.VelbusModule.VMBDALI import VMBDALI as VMBDALI_mod
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
from velbus.VelbusMessage.ModuleType import ModuleType
from velbus.VelbusMessage.ModuleInfo.VMBDALI import VMBDALI as VMBDALI_mi
from velbus.VelbusMessage.DaliDeviceSettingsRequest import DaliDeviceSettingsRequest
from velbus.VelbusMessage.DaliDeviceSettings import DaliDeviceSettings, DaliDeviceSettingValueLevel


_ = VMBDALI_mod  # load module to enable processing


@pytest.fixture(params=[1, 64])
def addr_channel(request):
    return request.param


def VMBDALI_module_info_exchange(module_address):
    return (
        VelbusFrame(
            address=module_address,
            message=ModuleTypeRequest(),
        ).to_bytes(),
        VelbusFrame(
            address=module_address,
            message=ModuleType(
                module_info=VMBDALI_mi(),
            ),
        ).to_bytes()
    )


@pytest.mark.asyncio
async def test_type(generate_sanic_request, mock_velbus, module_address):
    mock_velbus.set_expected_conversation([
        VMBDALI_module_info_exchange(module_address),
    ])

    sanic_req = generate_sanic_request(method='GET')
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/type")
    assert resp.status == 200
    assert resp.body.decode('utf-8') == f"VMBDALI at 0x{module_address:02x}\r\n"
    mock_velbus.assert_conversation_happened_exactly()


@pytest.mark.asyncio
async def test_dimvalue_GET(generate_sanic_request, mock_velbus, module_address, addr_channel):
    level = 123
    mock_velbus.set_expected_conversation([
        VMBDALI_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=DaliDeviceSettingsRequest(
                    channel=addr_channel,
                    source=DaliDeviceSettingsRequest.Source.Device,
                ),
            ).to_bytes(),
            [
                VelbusFrame(
                    address=module_address,
                    message=DaliDeviceSettings(
                        channel=addr_channel,
                        setting=DaliDeviceSettings.Setting.PowerOnLevel,
                        setting_value=DaliDeviceSettingValueLevel(7),
                    ),
                ).to_bytes(),
                VelbusFrame(
                    address=module_address,
                    message=DaliDeviceSettings(
                        channel=addr_channel,
                        setting=DaliDeviceSettings.Setting.ActualLevel,
                        setting_value=DaliDeviceSettingValueLevel(level),
                    ),
                ).to_bytes(),
            ]
        ),
    ])

    sanic_req = generate_sanic_request(method='GET')
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{addr_channel}/dimvalue")
    assert resp.status == 200
    assert resp.body.decode('utf-8') == str(level)
    mock_velbus.assert_conversation_happened_exactly()

