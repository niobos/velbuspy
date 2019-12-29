import asyncio
import datetime
import json

import freezegun
import pytest

import sanic.response
import sanic.exceptions

from velbus import HttpApi
from velbus.VelbusMessage._types import Index
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
from velbus.VelbusMessage.ModuleType import ModuleType
from velbus.VelbusMessage.ModuleInfo.VMB4DC import VMB4DC as VMB4DC_mi
from velbus.VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from velbus.VelbusMessage.SetDimvalue import SetDimvalue
from velbus.VelbusMessage.DimmercontrollerStatus import DimmercontrollerStatus
from velbus.VelbusModule.VMB4DC import VMB4DC as VMB4DC_mod

from .. import utils

_ = VMB4DC_mod  # load module to enable processing


def VMB4DC_module_info_exchange(module_address):
    return (
        VelbusFrame(
            address=module_address,
            message=ModuleTypeRequest(),
        ).to_bytes(),
        VelbusFrame(
            address=module_address,
            message=ModuleType(
                module_info=VMB4DC_mi(),
            ),
        ).to_bytes()
    )


@pytest.fixture(params=[1, 2, 3, 4])
def channel(request):
    return request.param


@pytest.mark.asyncio
async def test_get_dimvalue(generate_sanic_request, mock_velbus, module_address, channel):
    mock_velbus.set_expected_conversation([
        VMB4DC_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=ModuleStatusRequest(
                    channel=Index(8)(channel).to_int(),
                ),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=DimmercontrollerStatus(
                    channel=channel,
                    dimvalue=channel * 10,
                ),
            ).to_bytes()
        ),
    ])

    sanic_req = generate_sanic_request(method='GET')
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{channel}/dimvalue")
    assert 200 == resp.status
    assert str(channel*10) == resp.body.decode('utf-8')
    mock_velbus.assert_conversation_happened_exactly()


@pytest.mark.asyncio
async def test_put_dimvalue_int(generate_sanic_request, mock_velbus, module_address, channel):
    mock_velbus.set_expected_conversation([
        VMB4DC_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=SetDimvalue(
                    channel=channel,
                    dimvalue=100,
                    dimspeed=0,
                ),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=DimmercontrollerStatus(
                    channel=channel,
                    dimvalue=100,
                ),
            ).to_bytes()
         ),
    ])

    sanic_req = generate_sanic_request(method='PUT', body='100')
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{channel}/dimvalue")
    assert resp.status // 100 == 2

    mock_velbus.assert_conversation_happened_exactly()


@pytest.mark.asyncio
async def test_put_dimvalue_invalid_json(generate_sanic_request, mock_velbus, module_address, channel):
    mock_velbus.set_expected_conversation([
        VMB4DC_module_info_exchange(module_address),
    ])
    sanic_req = generate_sanic_request(
        method='PUT',
        body='{"Malformed JSON": true',
    )
    with pytest.raises(sanic.exceptions.InvalidUsage):
        _ = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f'/{channel}/dimvalue')
    mock_velbus.assert_conversation_happened_exactly()


@pytest.mark.asyncio
async def test_put_dimvalue_dict(generate_sanic_request, mock_velbus, module_address, channel):
    mock_velbus.set_expected_conversation([
        VMB4DC_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=SetDimvalue(
                    channel=channel,
                    dimvalue=100,
                    dimspeed=5,
                )
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=DimmercontrollerStatus(
                    channel=channel,
                    dimvalue=100,
                ),
            ).to_bytes(),
        ),
    ])

    sanic_req = generate_sanic_request(
        method='PUT',
        body=json.dumps({"dimvalue": 100, "dimspeed": 5})
    )
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{channel}/dimvalue")
    assert resp.status // 100 == 2

    mock_velbus.assert_conversation_happened_exactly()


@pytest.mark.asyncio
async def test_put_dimvalue_dict_invalid(generate_sanic_request, mock_velbus, module_address, channel):
    mock_velbus.set_expected_conversation([
        VMB4DC_module_info_exchange(module_address),
    ])

    sanic_req = generate_sanic_request(
        method='PUT',
        body=json.dumps({"dimvalue": 100, "foobar": True}),
    )
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f'/{channel}/dimvalue')
    assert resp.status == 400
    mock_velbus.assert_conversation_happened_exactly()


@pytest.mark.asyncio
async def test_put_dimvalue_list_single(generate_sanic_request, mock_velbus, module_address, channel):
    mock_velbus.set_expected_conversation([
        VMB4DC_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=SetDimvalue(
                    channel=channel,
                    dimvalue=100,
                    dimspeed=5,
                )
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=DimmercontrollerStatus(
                    channel=channel,
                    dimvalue=100,
                ),
            ).to_bytes(),
        ),
    ])

    sanic_req = generate_sanic_request(
        method='PUT',
        body=json.dumps([{"dimvalue": 100, "dimspeed": 5}])
    )
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{channel}/dimvalue")
    assert resp.status // 100 == 2

    mock_velbus.assert_conversation_happened_exactly()


@freezegun.freeze_time("2000-01-01 00:00:00", tick=True)
@pytest.mark.asyncio
async def test_put_dimvalue_list(generate_sanic_request, mock_velbus, module_address, channel):
    mock_velbus.set_expected_conversation([
        VMB4DC_module_info_exchange(module_address),
    ])

    sanic_req = generate_sanic_request(
        method='PUT',
        body=json.dumps([
            {"dimvalue": 100},
            {"dimvalue": 20, "when": "2000-01-01 00:00:00.1"}
        ])
    )
    # Do call to wrong endpoint
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{channel}/dimvalue")
    mock_velbus.assert_conversation_happened_exactly()
    assert 400 == resp.status

    mock_velbus.set_expected_conversation([
        (
            VelbusFrame(
                address=module_address,
                message=SetDimvalue(
                    channel=channel,
                    dimvalue=100,
                    dimspeed=0,
                )
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=DimmercontrollerStatus(
                    channel=channel,
                    dimvalue=100,
                ),
            ).to_bytes(),
        ),
    ])
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{channel}/e_dimvalue")
    assert 202 == resp.status

    await asyncio.sleep(0.05)
    mock_velbus.assert_conversation_happened_exactly()

    mock_velbus.set_expected_conversation([
        (
            VelbusFrame(
                address=module_address,
                message=SetDimvalue(
                    channel=channel,
                    dimvalue=20,
                    dimspeed=0,
                )
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=DimmercontrollerStatus(
                    channel=channel,
                    dimvalue=20,
                )
            ).to_bytes()
        ),
    ])

    await asyncio.sleep(0.1)  # until 0.15
    mock_velbus.assert_conversation_happened_exactly()

    assert len(HttpApi.modules[module_address].result().submodules[channel].delayed_calls) == 0


@freezegun.freeze_time("2000-01-01 00:00:00", tick=True)
@pytest.mark.asyncio
async def test_put_dimvalue_list_cancel(generate_sanic_request, mock_velbus, module_address, channel):
    mock_velbus.set_expected_conversation([
        VMB4DC_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=SetDimvalue(
                    channel=channel,
                    dimvalue=100,
                    dimspeed=0,
                )
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=DimmercontrollerStatus(
                    channel=channel,
                    dimvalue=100,
                )
            ).to_bytes()
        ),
    ])

    sanic_req = generate_sanic_request(
        method='PUT',
        body=json.dumps([
            {"dimvalue": 100},
            {"dimvalue": 20, "when": "2000-01-01 00:00:00.1"}
        ])
    )
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{channel}/e_dimvalue")
    assert 202 == resp.status

    await asyncio.sleep(0.05)
    mock_velbus.assert_conversation_happened_exactly()

    # Now interrupt this sleep with a new HTTP-call
    sanic_req = generate_sanic_request(
        method='PUT',
        body='42'
    )
    mock_velbus.set_expected_conversation([
        (
            VelbusFrame(
                address=module_address,
                message=SetDimvalue(
                    channel=channel,
                    dimvalue=42,
                    dimspeed=0,
                ),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=DimmercontrollerStatus(
                    channel=channel,
                    dimvalue=42,
                )
            ).to_bytes()
        ),
    ])

    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{channel}/e_dimvalue")
    assert resp.status // 100 == 2

    await asyncio.sleep(0.1)  # until 0.15
    mock_velbus.assert_conversation_happened_exactly()

    assert len(HttpApi.modules[module_address].result().submodules[channel].delayed_calls) == 0


@pytest.mark.asyncio
async def test_get_edimvalue(generate_sanic_request, mock_velbus, module_address, channel):
    sanic_req = generate_sanic_request(
        method='PUT',
        body=json.dumps([
            {"dimvalue": 100},
            {"dimvalue": 20, "when": datetime.datetime.now().isoformat()}
        ])
    )
    mock_velbus.set_expected_conversation([
        VMB4DC_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=SetDimvalue(
                    channel=channel,
                    dimvalue=100,
                    dimspeed=0,
                )
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=DimmercontrollerStatus(
                    channel=channel,
                    dimvalue=100,
                )
            ).to_bytes()
        ),
    ])
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{channel}/e_dimvalue")
    assert resp.status // 100 == 2

    sanic_req = generate_sanic_request()
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{channel}/delayed_calls")
    assert resp.status == 200

    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{channel}/e_dimvalue")
    assert resp.status == 200
    resp = json.loads(resp.body)
    assert len(resp) >= 1  # maybe the "now" action is still in the list, maybe it has already happened
    assert resp[-1]['dimvalue'] == 20
    assert isinstance(resp[-1]['when'], str)
