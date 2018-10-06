import pytest
from unittest.mock import patch, MagicMock, Mock

import asyncio
import sanic.request

from velbus import HttpApi
from velbus.VelbusProtocol import VelbusHttpProtocol
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
from velbus.VelbusMessage.ModuleType import ModuleType
from velbus.VelbusMessage.ModuleInfo.VMB4RYNO import VMB4RYNO as VMB4RYNO_mi
from velbus.VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from velbus.VelbusMessage.RelayStatus import RelayStatus

from velbus.VelbusModule.VMB4RYNO import VMB4RYNO as VMB4RYNO_mod


@pytest.fixture
def clean_http_api(request):
    del request  # unused
    HttpApi.modules.clear()
    HttpApi.ws_clients.clear()
    yield
    # leave dirty


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


@pytest.fixture
def sanic_req(request):
    del request  # unused
    req = sanic.request.Request(b'/modules/01/', {}, 1.1, 'GET', None)
    req._socket = None
    req._ip = '127.0.0.1'
    req._port = 9
    return req


def make_awaitable(ret) -> asyncio.Future:
    f = asyncio.get_event_loop().create_future()
    f.set_result(ret)
    return f


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
        assert resp.body == b'1\r\n2\r\n3\r\n4\r\n5\r\ntype\r\n'

        resp = await HttpApi.module_req(sanic_req, '11', '/')
        assert resp.body == b'1\r\n2\r\n3\r\n4\r\n5\r\ntype\r\n'

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
    resp = await HttpApi.module_req(sanic_req, '11', '/1/type')
    assert b'VMB4RYNO at 0x11\r\n' in resp.body


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
                relay=4,
                relay_status=RelayStatus.RelayStatus.On,
            ))
        HttpApi.modules[0x11].result().message(ret)
        return make_awaitable(ret)
    velbus_query.called = 0

    with patch('velbus.VelbusProtocol.VelbusHttpProtocol.velbus_query', new=velbus_query):
        resp = await HttpApi.module_req(sanic_req, '11', '/4/relay')
        assert resp.body == b'true'
        assert velbus_query.called == 1


@pytest.mark.asyncio
@pytest.mark.usesfixtures('vmb4ryno_11_http_api')
async def test_ws(sanic_req):
    HttpApi.message(VelbusFrame(address=0x11, message=RelayStatus(
        relay=4,
        relay_status=RelayStatus.RelayStatus.Off,
    )))

    ws = Mock()
    ws.subscribed_modules = {0x11}
    ws.send = Mock(return_value=make_awaitable(None))

    HttpApi.ws_clients.add(ws)
    await HttpApi.ws_client_listen_module(VelbusHttpProtocol(sanic_req), 0x11, ws)
    ws.send.assert_called_once_with('[{"op": "add", "path": "/11", "value": {"4": {"relay": false}}}]')
    ws.send.reset_mock()

    HttpApi.message(VelbusFrame(address=0x11, message=RelayStatus(
        relay=4,
        relay_status=RelayStatus.RelayStatus.On,
    )))
    ws.send.assert_called_once_with('[{"op": "add", "path": "/11/4/relay", "value": true}]')
    ws.send.reset_mock()

    HttpApi.message(VelbusFrame(address=0x11, message=RelayStatus(
        relay=4,
        relay_status=RelayStatus.RelayStatus.Off,
    )))
    ws.send.assert_called_once_with('[{"op": "add", "path": "/11/4/relay", "value": false}]')
    ws.send.reset_mock()
