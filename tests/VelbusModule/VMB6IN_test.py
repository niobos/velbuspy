import pytest

from velbus import HttpApi
from velbus.VelbusMessage._types import Index, Bitmap
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
from velbus.VelbusMessage.ModuleType import ModuleType
from velbus.VelbusMessage.ModuleInfo.VMB6IN import VMB6IN as VMB6IN_mi
from velbus.VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from velbus.VelbusMessage.ModuleStatus import ModuleStatus6IN
from velbus.VelbusModule.VMB6IN import VMB6IN as VMB6IN_mod

from .. import utils

_ = VMB6IN_mod  # load module to enable processing


def VMB6IN_module_info_exchange(module_address):
    return (
        VelbusFrame(
            address=module_address,
            message=ModuleTypeRequest(),
        ).to_bytes(),
        VelbusFrame(
            address=module_address,
            message=ModuleType(
                module_info=VMB6IN_mi(),
            ),
        ).to_bytes()
    )


@pytest.fixture(params=[1, 2, 3, 4, 5, 6])
def channel(request):
    return request.param


@pytest.fixture(params=[True, False])
def input_state(request):
    return request.param


@pytest.mark.asyncio
async def test_get_input(generate_sanic_request, mock_velbus, module_address, channel, input_state):
    input_state_bit = 1 if input_state else 0
    input_state_json = 'true' if input_state else 'false'

    mock_velbus.set_expected_conversation([
        VMB6IN_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=ModuleStatusRequest(
                    channel=0x3f,
                ),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=ModuleStatus6IN(
                    input_status=Bitmap(8).from_int(input_state_bit << (channel-1))
                ),
            ).to_bytes()
        ),
    ])

    sanic_req = generate_sanic_request(method='GET')
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{channel}/input")
    assert resp.status == 200
    assert resp.body.decode('utf-8') == input_state_json
    mock_velbus.assert_conversation_happened_exactly()
