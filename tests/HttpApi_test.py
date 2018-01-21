import asyncio
import datetime
import pytest
import sanic.request
from unittest.mock import patch

from velbus import HttpApi
from velbus.VelbusProtocol import VelbusHttpProtocol
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
from velbus.VelbusMessage.ModuleType import ModuleType
from velbus.VelbusMessage.ModuleInfo.VMB4RYNO import VMB4RYNO as VMB4RYNO_mi
from velbus.VelbusModule.VMB4RYNO import VMB4RYNO as VMB4RYNO_mod
from velbus.CachedException import CachedTimeoutError


@pytest.fixture(scope='function')
def clean_http_api(request):
    HttpApi.modules.clear()
    HttpApi.ws_clients.clear()
    yield
    # leave dirty


def make_awaitable(ret) -> asyncio.Future:
    f = asyncio.get_event_loop().create_future()
    f.set_result(ret)
    return f


def give_request_ip(req: sanic.request):
    req._socket = None
    req._ip = '127.0.0.1'
    req._port = 9


@pytest.mark.asyncio
@pytest.mark.usefixtures('clean_http_api')
async def test_get_module():
    req = sanic.request.Request(b'/modules/01/', {}, 1.1, 'GET', None)
    give_request_ip(req)

    def velbus_query(self,
                     question: VelbusFrame,
                     response_type: type,
                     response_address: int = None,
                     timeout: int = 2,
                     additional_check=(lambda vbm: True)):
        assert question == VelbusFrame(address=1, message=ModuleTypeRequest())
        return make_awaitable(
            VelbusFrame(address=1, message=ModuleType(module_info=VMB4RYNO_mi()))
        )

    with patch('velbus.VelbusProtocol.VelbusHttpProtocol.velbus_query', new=velbus_query):
        bus = VelbusHttpProtocol(req)
        mod = await HttpApi.get_module(bus, 1)
        assert isinstance(mod, VMB4RYNO_mod)


@pytest.mark.asyncio
@pytest.mark.usefixtures('clean_http_api')
async def test_get_module_timeout():
    req = sanic.request.Request(b'/modules/aA/', {}, 1.1, 'GET', None)
    give_request_ip(req)

    with patch('velbus.VelbusProtocol.VelbusHttpProtocol.process_message') as velbus_pm:
        start_time = datetime.datetime.now()
        with pytest.raises(CachedTimeoutError):
            _ = await HttpApi.module_req(req, 'aA', '')
        duration = (datetime.datetime.now() - start_time).total_seconds()
        assert (2 * .9 < duration < 2 * 1.1)  # give 10% slack

        velbus_pm.assert_called_with(VelbusFrame(
            address=0xaa,
            message=ModuleTypeRequest(),
        ))

        start_time = datetime.datetime.now()
        with pytest.raises(CachedTimeoutError):
            _ = await HttpApi.module_req(req, 'Aa', '')
        duration = (datetime.datetime.now() - start_time).total_seconds()
        assert (duration < .1)  # Should return immediately


@pytest.mark.asyncio
@pytest.mark.usefixtures('clean_http_api')
async def test_get_module_parallel_timeout():
    req = sanic.request.Request(b'/modules/aA/', {}, 1.1, 'GET', None)
    give_request_ip(req)

    with patch('velbus.VelbusProtocol.VelbusHttpProtocol.process_message'):
        start_time = datetime.datetime.now()

        async def delayed_call(delay: int):
            await asyncio.sleep(delay)
            return await HttpApi.module_req(req, 'aA', '')

        await asyncio.gather(
            delayed_call(0),
            delayed_call(1),
            return_exceptions=True
        )
        duration = (datetime.datetime.now() - start_time).total_seconds()
        assert (2 * .9 < duration < 2 * 1.1)  # give 10% slack
