import json
import random

import pytest
import asyncio
from unittest.mock import patch
import sanic.response
import sanic.exceptions

from velbus import HttpApi
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleInfo.VMB4DC import VMB4DC as VMB4DC_mi
from velbus.VelbusMessage.SetDimvalue import SetDimvalue
from velbus.VelbusModule.VMB4DC import VMB4DC as VMB4DC_mod

from ..utils import make_awaitable


@pytest.fixture(params=[1, 2, 3, 4])
def subaddress(request):
    return request.param


@pytest.fixture(params=[0, 1])  # test with at least 2 values
def magic_str(request):
    start = 1E6 * request.param
    return str(random.randint(start, start + 1E6))


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
@pytest.mark.usefixtures('vmb4dc_11_http_api')
async def test_put_dimvalue_int(sanic_req, subaddress):
    with patch('velbus.VelbusProtocol.VelbusProtocol.velbus_query',
               return_value=make_awaitable(None), autospec=True) as query:
        sanic_req.method = 'PUT'
        sanic_req.body = '100'
        resp = await HttpApi.module_req(sanic_req, '11', f"/{subaddress}/dimvalue")
        assert 202 == resp.status

        await HttpApi.modules[0x11].result().submodules[subaddress].queue_processing_task
        query.assert_called_once()
        assert VelbusFrame(
                address=0x11,
                message=SetDimvalue(
                    channel=subaddress,
                    dimvalue=100,
                    dimspeed=0,
                ),
            ) == query.call_args[0][1]


@pytest.mark.asyncio
@pytest.mark.usefixtures('vmb4dc_11_http_api')
async def test_put_dimvalue_invalid_json(sanic_req):
    def velbus_query(self,
                     question: VelbusFrame,
                     response_type: type,
                     response_address: int = None,
                     timeout: int = 2,
                     additional_check=(lambda vbm: True)):
        del self, response_type, response_address, timeout, additional_check  # unused
        velbus_query.called += 1
        assert VelbusFrame(
                address=0x11,
                message=None,
            ) == question
        return make_awaitable(None)
    velbus_query.called = 0

    with patch('velbus.VelbusProtocol.VelbusHttpProtocol.velbus_query', new=velbus_query):
        sanic_req.method = 'PUT'
        sanic_req.body = '{"Malformed JSON": true'
        with pytest.raises(sanic.exceptions.InvalidUsage):
            _ = await HttpApi.module_req(sanic_req, '11', '/4/dimvalue')
        assert 0 == velbus_query.called


@pytest.mark.asyncio
@pytest.mark.usefixtures('vmb4dc_11_http_api')
async def test_put_dimvalue_dict(sanic_req, subaddress):
    with patch('velbus.VelbusProtocol.VelbusProtocol.velbus_query',
               return_value=make_awaitable(None), autospec=True) as query:
        sanic_req.method = 'PUT'
        sanic_req.body = json.dumps({"dimvalue": 100, "dimspeed": 5})
        resp = await HttpApi.module_req(sanic_req, '11', f"/{subaddress}/dimvalue")
        assert 202 == resp.status

        await HttpApi.modules[0x11].result().submodules[subaddress].queue_processing_task
        query.assert_called_once()
        assert VelbusFrame(
            address=0x11,
            message=SetDimvalue(
                channel=subaddress,
                dimvalue=100,
                dimspeed=5,
            ),
        ) == query.call_args[0][1]


@pytest.mark.asyncio
@pytest.mark.usefixtures('vmb4dc_11_http_api')
async def test_put_dimvalue_dict_invalid(sanic_req):
    with patch('velbus.VelbusProtocol.VelbusHttpProtocol.velbus_query',
               return_value=make_awaitable(None), autospec=True) as query:
        sanic_req.method = 'PUT'
        sanic_req.body = json.dumps({"dimvalue": 100, "foobar": True})
        resp = await HttpApi.module_req(sanic_req, '11', '/4/dimvalue')
        assert resp.status == 400
        query.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.usefixtures('vmb4dc_11_http_api')
async def test_put_dimvalue_list_single(sanic_req, subaddress):
    with patch('velbus.VelbusProtocol.VelbusProtocol.velbus_query',
               return_value=make_awaitable(None), autospec=True) as query:
        sanic_req.method = 'PUT'
        sanic_req.body = json.dumps([{"dimvalue": 100, "dimspeed": 5}])
        resp = await HttpApi.module_req(sanic_req, '11', f"/{subaddress}/dimvalue")
        assert 202 == resp.status

        await HttpApi.modules[0x11].result().submodules[subaddress].queue_processing_task
        query.assert_called_once()
        assert VelbusFrame(
                address=0x11,
                message=SetDimvalue(
                    channel=subaddress,
                    dimvalue=100,
                    dimspeed=5,
                ),
            ) == query.call_args[0][1]


@pytest.mark.asyncio
@pytest.mark.usefixtures('vmb4dc_11_http_api')
async def test_put_dimvalue_list(sanic_req, subaddress, magic_str):
    fake_sleep_is_called = None
    fake_sleep_returns = None

    def setup_fake_sleep():
        nonlocal fake_sleep_is_called, fake_sleep_returns
        fake_sleep_is_called = asyncio.get_event_loop().create_future()
        fake_sleep_returns = None

    def fake_sleep(amount):
        nonlocal fake_sleep_is_called, fake_sleep_returns
        fake_sleep_is_called.set_result(True)
        fake_sleep_returns = asyncio.get_event_loop().create_future()
        return fake_sleep_returns

    with \
            patch('velbus.VelbusProtocol.VelbusProtocol.velbus_query',
                  return_value=make_awaitable(None), autospec=True) as query, \
            patch('asyncio.sleep', side_effect=fake_sleep) as fsleep:
        sanic_req.method = 'PUT'
        sanic_req.body = json.dumps([
            {"dimvalue": 100, "timeout": 1},
            {"dimvalue": 20}
        ])
        resp = await HttpApi.module_req(sanic_req, '11', f"/{subaddress}/dimvalue")
        query.assert_not_called()
        assert 400 == resp.status

        setup_fake_sleep()
        resp = await HttpApi.module_req(sanic_req, '11', f"/{subaddress}/e_dimvalue")
        assert 202 == resp.status
        # process_queue is now running async
        # It will block on the fake_sleep future to be resolved

        await fake_sleep_is_called
        # We are at the first sleep() call, inspect
        fsleep.assert_called_once_with(1)
        query.assert_called_once()
        assert VelbusFrame(
                address=0x11,
                message=SetDimvalue(
                    channel=subaddress,
                    dimvalue=100,
                    dimspeed=0,
                ),
            ) == query.call_args[0][1]
        # Sleep is done, next step
        fake_sleep_returns.set_result(None)
        setup_fake_sleep()
        fsleep.reset_mock()
        query.reset_mock()

        await fake_sleep_is_called
        # we are at the second sleep() call, inspect
        fsleep.assert_called_once_with(0)
        query.assert_called_once()
        assert VelbusFrame(
                address=0x11,
                message=SetDimvalue(
                    channel=subaddress,
                    dimvalue=20,
                    dimspeed=0,
                ),
            ) == query.call_args[0][1]
        # Sleep is done, next step
        fake_sleep_returns.set_result(None)

        # Last step done, queue should resolve now:
        await HttpApi.modules[0x11].result().submodules[subaddress].queue_processing_task


@pytest.mark.asyncio
@pytest.mark.usefixtures('vmb4dc_11_http_api')
async def test_put_dimvalue_list_cancel(sanic_req, subaddress, magic_str):
    fake_sleep_is_called = None
    fake_sleep_returns = None

    def setup_fake_sleep():
        nonlocal fake_sleep_is_called, fake_sleep_returns
        fake_sleep_is_called = asyncio.get_event_loop().create_future()
        fake_sleep_returns = None

    def fake_sleep(amount):
        nonlocal fake_sleep_is_called, fake_sleep_returns
        fake_sleep_is_called.set_result(True)
        fake_sleep_returns = asyncio.get_event_loop().create_future()
        return fake_sleep_returns

    with \
            patch('velbus.VelbusProtocol.VelbusProtocol.velbus_query',
                  return_value=make_awaitable(None), autospec=True) as query, \
            patch('asyncio.sleep', side_effect=fake_sleep) as fsleep:
        sanic_req.method = 'PUT'
        sanic_req.body = json.dumps([
            {"dimvalue": 100, "timeout": 2},
            {"dimvalue": 20}
        ])
        setup_fake_sleep()
        resp = await HttpApi.module_req(sanic_req, '11', f"/{subaddress}/e_dimvalue")
        assert 202 == resp.status
        # process_queue is now running async
        # It will block on the fake_sleep future to be resolved

        await fake_sleep_is_called
        # We are at the first sleep() call, send interrupting second call
        fsleep.assert_called_once_with(2)
        fsleep.reset_mock()
        query.reset_mock()
        sanic_req.body = '42'
        sanic_req.parsed_json = None  # Reset JSON parser to re-parse '42'
        resp = await HttpApi.module_req(sanic_req, '11', f"/{subaddress}/e_dimvalue")
        assert 202 == resp.status
        # Sleep is done, next step
        assert fake_sleep_returns.cancelled()
        setup_fake_sleep()

        await fake_sleep_is_called
        # we are at the first sleep() call after the interrupting call, inspect
        fsleep.assert_called_once_with(0)
        query.assert_called_once()
        assert VelbusFrame(
                address=0x11,
                message=SetDimvalue(
                    channel=subaddress,
                    dimvalue=42,
                    dimspeed=0,
                ),
            ) == query.call_args[0][1]
        # Sleep is done, next step
        fake_sleep_returns.set_result(None)

        # Last step done, queue should resolve now:
        await HttpApi.modules[0x11].result().submodules[subaddress].queue_processing_task
