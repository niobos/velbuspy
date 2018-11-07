import json

import pytest
import asyncio
import sanic.response
import sanic.exceptions

from velbus import HttpApi
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
from velbus.VelbusMessage.ModuleType import ModuleType
from velbus.VelbusMessage.ModuleInfo.VMB4DC import VMB4DC as VMB4DC_mi
from velbus.VelbusMessage.SetDimvalue import SetDimvalue
from velbus.VelbusMessage.DimmercontrollerStatus import DimmercontrollerStatus
from velbus.VelbusModule.VMB4DC import VMB4DC as VMB4DC_mod


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


@pytest.fixture
def vmb4dc_11_http_api(request):
    del request  # unused
    HttpApi.modules.clear()
    HttpApi.ws_clients.clear()

    HttpApi.modules[0x11] = asyncio.get_event_loop().create_future()
    HttpApi.modules[0x11].set_result(
        VMB4DC_mod(bus=None, address=0x11, module_info=VMB4DC_mi(),
                   update_state_cb=HttpApi.gen_update_state_cb(0x11))
    )

    yield
    # leave dirty


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
    assert 202 == resp.status

    await HttpApi.modules[module_address].result().submodules[channel].queue_processing_task
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
    assert 202 == resp.status

    await HttpApi.modules[module_address].result().submodules[channel].queue_processing_task
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
    assert 202 == resp.status

    await HttpApi.modules[module_address].result().submodules[channel].queue_processing_task
    mock_velbus.assert_conversation_happened_exactly()


@pytest.mark.asyncio
async def test_put_dimvalue_list(generate_sanic_request, mock_velbus, module_address, channel,
                                 fake_asyncio_sleep):
    mock_velbus.set_expected_conversation([
        VMB4DC_module_info_exchange(module_address),
    ])

    sanic_req = generate_sanic_request(
        method='PUT',
        body=json.dumps([
            {"dimvalue": 100, "timeout": 1},
            {"dimvalue": 20}
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
    # process_queue is now running async
    # Wait until it calls asyncio.sleep()

    sleep_call = await fake_asyncio_sleep.new_sleep_call(from_function='process_queue')
    # We are at the first sleep() call, inspect
    assert 1 == sleep_call.delay
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
    sleep_call.return_asap()  # Consider sleep() to be done
    # process_queue will now set the next dimvalue, and call asyncio.sleep(0)

    sleep_call = await fake_asyncio_sleep.new_sleep_call(from_function='process_queue')
    # we are at the second sleep() call, inspect
    assert 0 == sleep_call.delay
    mock_velbus.assert_conversation_happened_exactly()

    sleep_call.return_asap()  # Consider sleep() to be done

    # Last step done, queue should resolve now:
    await HttpApi.modules[module_address].result().submodules[channel].queue_processing_task


@pytest.mark.asyncio
async def test_put_dimvalue_list_cancel(generate_sanic_request, mock_velbus, module_address, channel,
                                        fake_asyncio_sleep):
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
            {"dimvalue": 100, "timeout": 11},
            {"dimvalue": 20}
        ])
    )
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{channel}/e_dimvalue")
    assert 202 == resp.status
    # process_queue is now running async
    # Wait until it calls asyncio.sleep()

    sleep_call = await fake_asyncio_sleep.new_sleep_call(from_function='process_queue')
    # We are at the first sleep() call, inspect
    assert 11 == sleep_call.delay
    mock_velbus.assert_conversation_happened_exactly()

    # Now interrupt this sleep with a new HTTP-call
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
    sanic_req = generate_sanic_request(
        method='PUT',
        body='42'
    )
    old_sleep_call = sleep_call
    resp = await HttpApi.module_req(sanic_req, f'{module_address:02x}', f"/{channel}/e_dimvalue")
    assert 202 == resp.status
    # process_queue is now running async
    # Wait until it calls asyncio.sleep()
    sleep_call = await fake_asyncio_sleep.new_sleep_call(from_function='process_queue')

    # we are at the first sleep() call after the interrupting call, inspect
    assert old_sleep_call.cancelled()
    assert 0 == sleep_call.delay
    mock_velbus.assert_conversation_happened_exactly()
    sleep_call.return_asap()

    # Last step done, queue should resolve now:
    await HttpApi.modules[module_address].result().submodules[channel].queue_processing_task
