import pytest
from unittest.mock import patch, Mock

import asyncio
import sanic.response

from velbus import HttpApi
from velbus.VelbusProtocol import VelbusHttpProtocol
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
from velbus.VelbusMessage.ModuleType import ModuleType
from velbus.VelbusMessage.ModuleInfo.VMB4RYNO import VMB4RYNO as VMB4RYNO_mi
from velbus.VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from velbus.VelbusMessage.RelayStatus import RelayStatus
from velbus.VelbusMessage.SwitchRelay import SwitchRelay
from velbus.VelbusMessage.StartRelayTimer import StartRelayTimer

from velbus.VelbusModule.VMB4RYNO import VMB4RYNO as VMB4RYNO_mod

from ..utils import make_awaitable


@pytest.fixture(params=[1, 2, 3, 4, 5])
def subaddress(request):
    return request.param


@pytest.fixture
def vmb4ryno_11_http_api(request):
    del request  # unused
    HttpApi.modules.clear()
    HttpApi.ws_clients.clear()

    HttpApi.modules[0x11] = asyncio.get_event_loop().create_future()
    HttpApi.modules[0x11].set_result(
        VMB4RYNO_mod(bus=None, address=0x11, module_info=VMB4RYNO_mi(),
                     update_state_cb=HttpApi.gen_update_state_cb(0x11))
    )

    yield
    # leave dirty


@pytest.mark.asyncio
@pytest.mark.usefixtures('clean_http_api')
async def test_get_module(sanic_req):
    def velbus_query(self,
                     question: VelbusFrame,
                     response_type: type,
                     response_address: int = None,
                     timeout: int = 2,
                     additional_check=(lambda vbm: True)):
        del self, response_type, response_address, timeout, additional_check  # unused
        velbus_query.called += 1
        assert question == VelbusFrame(address=0x11, message=ModuleTypeRequest())
        return make_awaitable(
            VelbusFrame(address=1, message=ModuleType(module_info=VMB4RYNO_mi()))
        )
    velbus_query.called = 0

    with patch('velbus.VelbusProtocol.VelbusHttpProtocol.velbus_query', new=velbus_query):
        resp = await HttpApi.module_req(sanic_req, '11', '')
        assert '1\r\n2\r\n3\r\n4\r\n5\r\ntype\r\n' == resp.body.decode('utf-8')

        resp = await HttpApi.module_req(sanic_req, '11', '/')
        assert '1\r\n2\r\n3\r\n4\r\n5\r\ntype\r\n' == resp.body.decode('utf-8')

        assert velbus_query.called == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures('vmb4ryno_11_http_api')
async def test_get_index(sanic_req):
    resp = await HttpApi.module_req(sanic_req, '11', '/1')
    assert b'type\r\n' in resp.body

    resp = await HttpApi.module_req(sanic_req, '11', '/1/')
    assert b'type\r\n' in resp.body


@pytest.mark.asyncio
@pytest.mark.usefixtures('vmb4ryno_11_http_api')
async def test_get_type(sanic_req):
    resp = await HttpApi.module_req(sanic_req, '11', '/type')
    assert 'VMB4RYNO at 0x11\r\n' in resp.body.decode('utf-8')
    resp = await HttpApi.module_req(sanic_req, '11', '/2/type')
    assert 'VMB4RYNOChannel at 0x11/2\r\n' in resp.body.decode('utf-8')


@pytest.mark.asyncio
@pytest.mark.usefixtures('vmb4ryno_11_http_api')
async def test_get_relay(sanic_req):
    def velbus_query(self,
                     question: VelbusFrame,
                     response_type: type,
                     response_address: int = None,
                     timeout: int = 2,
                     additional_check=(lambda vbm: True)):
        del self, response_type, response_address, timeout, additional_check  # unused
        velbus_query.called += 1
        assert question == VelbusFrame(address=0x11, message=ModuleStatusRequest(
            channel=1 << (4 - 1),
        ))
        ret = VelbusFrame(address=0x11, message=RelayStatus(
                channel=4,
                relay_status=RelayStatus.RelayStatus.On,
            ))
        HttpApi.modules[0x11].result().message(ret)
        return make_awaitable(ret)
    velbus_query.called = 0

    with patch('velbus.VelbusProtocol.VelbusHttpProtocol.velbus_query', new=velbus_query):
        resp = await HttpApi.module_req(sanic_req, '11', '/4/relay')
        assert 'true' == resp.body.decode('utf-8')
        assert velbus_query.called == 1


@pytest.mark.asyncio
@pytest.mark.usesfixtures('vmb4ryno_11_http_api')
async def test_ws(sanic_req):
    HttpApi.message(VelbusFrame(address=0x11, message=RelayStatus(
        channel=4,
        relay_status=RelayStatus.RelayStatus.Off,
    )))

    ws = Mock()
    ws.subscribed_modules = {0x11}
    ws.send = Mock(return_value=make_awaitable(None))

    HttpApi.ws_clients.add(ws)
    await HttpApi.ws_client_listen_module(VelbusHttpProtocol(sanic_req), 0x11, ws)
    ws.send.assert_called_once_with('[{"op": "add", "path": "/11", "value": {'
                                    '"1": {}, '
                                    '"2": {}, '
                                    '"3": {}, '
                                    '"4": {"relay": false}, '
                                    '"5": {}'
                                    '}}]')
    ws.send.reset_mock()

    HttpApi.message(VelbusFrame(address=0x11, message=RelayStatus(
        channel=4,
        relay_status=RelayStatus.RelayStatus.On,
    )))
    ws.send.assert_called_once_with('[{"op": "add", "path": "/11/4/relay", "value": true}]')
    ws.send.reset_mock()

    HttpApi.message(VelbusFrame(address=0x11, message=RelayStatus(
        channel=4,
        relay_status=RelayStatus.RelayStatus.Off,
    )))
    ws.send.assert_called_once_with('[{"op": "add", "path": "/11/4/relay", "value": false}]')
    ws.send.reset_mock()


@pytest.mark.asyncio
@pytest.mark.usefixtures('vmb4ryno_11_http_api')
async def test_put_relay_on(sanic_req, subaddress):
    response = sanic.response.HTTPResponse(body='magic')
    with \
            patch('velbus.VelbusProtocol.VelbusProtocol.velbus_query',
                  return_value=make_awaitable(None), autospec=True) as query, \
            patch('velbus.VelbusModule.VMB4RYNO.VMB4RYNOChannel.relay_GET',
                  return_value=make_awaitable(response), autospec=True):
        sanic_req.method = 'PUT'
        sanic_req.body = 'true'
        resp = await HttpApi.module_req(sanic_req, '11', f"/{subaddress}/relay")
        assert 200 == resp.status
        assert 'magic' == resp.body.decode('utf-8')

        query.assert_called_once()
        assert VelbusFrame(
                address=0x11,
                message=SwitchRelay(
                    command=SwitchRelay.Command.SwitchRelayOn,
                    channel=subaddress,

                ),
            ) == query.call_args[0][1]


@pytest.mark.asyncio
@pytest.mark.usefixtures('vmb4ryno_11_http_api')
async def test_put_relay_timer(sanic_req, subaddress):
    response = sanic.response.HTTPResponse(body='magic')
    with \
            patch('velbus.VelbusProtocol.VelbusProtocol.velbus_query',
                  return_value=make_awaitable(None), autospec=True) as query, \
            patch('velbus.VelbusModule.VMB4RYNO.VMB4RYNOChannel.relay_GET',
                  return_value=make_awaitable(response), autospec=True):
        sanic_req.method = 'PUT'
        sanic_req.body = '7'
        resp = await HttpApi.module_req(sanic_req, '11', f"/{subaddress}/relay")
        assert 200 == resp.status
        assert 'magic' == resp.body.decode('utf-8')

        query.assert_called_once()
        assert VelbusFrame(
                address=0x11,
                message=StartRelayTimer(
                    channel=subaddress,
                    delay_time=7,
                ),
            ) == query.call_args[0][1]
