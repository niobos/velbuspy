import datetime
import json

import freezegun
import pytest
from unittest.mock import patch, Mock, call

import asyncio
import sanic.response

from velbus import HttpApi
from velbus.VelbusProtocol import VelbusHttpProtocol
from velbus.VelbusMessage._types import Index, Bitmap
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
from velbus.VelbusMessage.ModuleType import ModuleType
from velbus.VelbusMessage.ModuleInfo.VMB4RYNO import VMB4RYNO as VMB4RYNO_mi
from velbus.VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from velbus.VelbusMessage.RelayStatus import RelayStatus
from velbus.VelbusMessage.SwitchRelay import SwitchRelay
from velbus.VelbusMessage.StartRelayTimer import StartRelayTimer
from velbus.VelbusMessage.PushButtonStatus import PushButtonStatus

from velbus.VelbusModule.VMB4RYNO import VMB4RYNO as VMB4RYNO_mod

from ..utils import make_awaitable


_ = VMB4RYNO_mod  # load module to enable processing


@pytest.fixture(params=[1, 2, 3, 4, 5])
def subaddress(request):
    return request.param


@pytest.fixture(params=[1, 2, 3, 4, 5])
def channel(request):
    return request.param


@pytest.fixture(params=[True, False])
def true_false(request):
    return request.param


@pytest.fixture
def vmb4ryno_11_http_api(request):
    del request  # unused
    HttpApi.modules.clear()
    HttpApi.ws_clients.clear()

    mod = VMB4RYNO_mod(bus=None, address=0x11, module_info=VMB4RYNO_mi())
    mod.state_callback.add(HttpApi.gen_update_state_cb(0x11))
    HttpApi.modules[0x11] = asyncio.get_event_loop().create_future()
    HttpApi.modules[0x11].set_result(mod)

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


def VMB4RYNO_module_info_exchange(module_address):
    return (
        VelbusFrame(
            address=module_address,
            message=ModuleTypeRequest(),
        ).to_bytes(),
        VelbusFrame(
            address=module_address,
            message=ModuleType(
                module_info=VMB4RYNO_mi(),
            ),
        ).to_bytes()
    )


@pytest.mark.asyncio
async def test_get_relay(generate_sanic_request, mock_velbus, module_address, channel):
    mock_velbus.set_expected_conversation([
        VMB4RYNO_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=ModuleStatusRequest(
                    channel=Index(8)(channel).to_int(),
                ),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=RelayStatus(
                    channel=channel,
                    relay_status=RelayStatus.RelayStatus.On,
                ),
            ).to_bytes()
        )
    ])

    sanic_req = generate_sanic_request()
    resp = await HttpApi.module_req(sanic_req, f"{module_address:02x}", f"/{channel}/relay")
    assert 200 == resp.status
    assert 'true' == resp.body.decode('utf-8')
    mock_velbus.assert_conversation_happened_exactly()


@pytest.mark.asyncio
async def test_ws(generate_sanic_request, mock_velbus):
    module_address = 0x11  # TODO: check for "all" addresses
    channel = 4  # TODO: check all channels
    mock_velbus.set_expected_conversation([
        VMB4RYNO_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=ModuleStatusRequest(
                    channel=Index(8)(channel).to_int(),
                ),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=RelayStatus(
                    channel=channel,
                    relay_status=RelayStatus.RelayStatus.Off,
                ),
            ).to_bytes()
        )
    ])
    # Initialize the module
    sanic_req = generate_sanic_request()
    resp = await HttpApi.module_req(sanic_req, f"{module_address:02x}", f"/{channel}/relay")

    ws = Mock()
    ws.subscribed_modules = {module_address}
    ws.send = Mock(return_value=make_awaitable(None))

    HttpApi.ws_clients.add(ws)
    sanic_req = generate_sanic_request()
    await HttpApi.ws_client_listen_module(VelbusHttpProtocol(sanic_req), module_address, ws)
    ws.send.assert_called_once_with('[{"op": "add", "path": "/11", "value": {'
                                    '"1": {}, '
                                    '"2": {}, '
                                    '"3": {}, '
                                    '"4": {"relay": false}, '
                                    '"5": {}'
                                    '}}]')
    ws.send.reset_mock()

    with freezegun.freeze_time("2000-01-01 00:00:00") as frozen_datetime:
        now = datetime.datetime.now().timestamp()

        HttpApi.message(VelbusFrame(address=module_address, message=RelayStatus(
            channel=channel,
            relay_status=RelayStatus.RelayStatus.On,
        )))
        ws.send.assert_has_calls([
            call('[{"op": "add", "path": "/11/4/relay", "value": true}]'),
            call('[{"op": "add", "path": "/11/4/last_change", "value": ' + str(now) + '}]'),
        ])
        ws.send.reset_mock()

        frozen_datetime.tick(datetime.timedelta(seconds=10))
        now = datetime.datetime.now().timestamp()
        HttpApi.message(VelbusFrame(address=module_address, message=RelayStatus(
            channel=channel,
            relay_status=RelayStatus.RelayStatus.Off,
        )))
        ws.send.assert_has_calls([
            call('[{"op": "add", "path": "/11/4/relay", "value": false}]'),
            call('[{"op": "add", "path": "/11/4/last_change", "value": ' + str(now) + '}]'),
        ])
        ws.send.reset_mock()


@pytest.mark.asyncio
async def test_put_relay(generate_sanic_request, mock_velbus, module_address, channel, true_false):
    mock_velbus.set_expected_conversation([
        VMB4RYNO_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=SwitchRelay(
                    command=SwitchRelay.Command.SwitchRelayOn if true_false
                    else SwitchRelay.Command.SwitchRelayOff,
                    channel=Index(8)(channel),
                ),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=RelayStatus(
                    channel=channel,
                    relay_status=RelayStatus.RelayStatus.On if true_false
                    else RelayStatus.RelayStatus.Off,
                ),
            ).to_bytes()
        )
    ])

    sanic_req = generate_sanic_request(method='PUT', body=json.dumps(true_false))
    resp = await HttpApi.module_req(sanic_req, f"{module_address:02x}", f"/{channel}/relay")
    assert resp.status == 200
    assert resp.body.decode('utf-8') == json.dumps(true_false)

    await asyncio.sleep(0.05)  # allow time to process the queue
    mock_velbus.assert_conversation_happened_exactly()


@pytest.mark.asyncio
async def test_put_relay_timer(generate_sanic_request, mock_velbus, module_address, channel):
    timer = 42

    mock_velbus.set_expected_conversation([
        VMB4RYNO_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=StartRelayTimer(
                    channel=channel,
                    delay_time=timer,
                ),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=RelayStatus(
                    channel=channel,
                    relay_status=RelayStatus.RelayStatus.On,
                ),
            ).to_bytes()
        )
    ])

    sanic_req = generate_sanic_request(method='PUT', body=str(timer))
    resp = await HttpApi.module_req(sanic_req, f"{module_address:02x}", f"/{channel}/relay")
    assert resp.status == 200
    assert resp.body.decode('utf-8') == 'true'

    await asyncio.sleep(0.05)  # allow time to process the queue
    mock_velbus.assert_conversation_happened_exactly()


@pytest.mark.asyncio
async def test_last_change(generate_sanic_request, mock_velbus, module_address, channel):
    mock_velbus.set_expected_conversation([
        VMB4RYNO_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=ModuleStatusRequest(
                    channel=Index(8)(channel).to_int(),
                ),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=RelayStatus(
                    channel=channel,
                    relay_status=RelayStatus.RelayStatus.On,
                ),
            ).to_bytes()
        )
    ])

    sanic_req = generate_sanic_request()
    resp = await HttpApi.module_req(sanic_req, f"{module_address:02x}", f"/{channel}/relay")
    assert resp.status == 200
    assert resp.body.decode('utf-8') == 'true'

    resp = await HttpApi.module_req(sanic_req, f"{module_address:02x}", f"/{channel}/last_change")
    assert resp.status == 200
    assert resp.body.decode('utf-8') == 'null'

    with freezegun.freeze_time("2000-01-01 00:00:00") as frozen_datetime:
        now = datetime.datetime.now().timestamp()

        HttpApi.message(VelbusFrame(
            address=module_address,
            message=PushButtonStatus(
                just_released=Bitmap(8).from_int(1 << (channel-1)),
            )
        ))

        resp = await HttpApi.module_req(sanic_req, f"{module_address:02x}", f"/{channel}/last_change")
        assert resp.status == 200
        assert resp.body.decode('utf-8') == str(now)
