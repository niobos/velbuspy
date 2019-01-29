import datetime

import pytest
from freezegun import freeze_time

from velbus.HttpApi import module_req, message
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
from velbus.VelbusMessage.ModuleType import ModuleType
from velbus.VelbusMessage.ModuleInfo.VMB1TS import VMB1TS as VMB1TS_mi
from velbus.VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from velbus.VelbusMessage.SensorTemperature import SensorTemperature
from velbus.VelbusMessage.SensorTemperatureRequest import SensorTemperatureRequest
from velbus.VelbusMessage.TemperatureSensorStatus import TemperatureSensorStatus
from velbus.VelbusMessage.PushButtonStatus import PushButtonStatus
from velbus.VelbusModule.VMB1TS import VMB1TS
from velbus.VelbusMessage._types import Bitmap


_ = VMB1TS  # dummy usage to force import
# import needed to auto-register the module for processing


def VMB1TS_module_info_exchange(module_address):
    return (
        VelbusFrame(
           address=module_address,
           message=ModuleTypeRequest(),
        ).to_bytes(),
        VelbusFrame(
           address=module_address,
           message=ModuleType(
               module_info=VMB1TS_mi(),
           ),
        ).to_bytes()
    )


@pytest.mark.asyncio
async def test_VMB1TS_instantiation(generate_sanic_request, module_address, mock_velbus):
    mock_velbus.set_expected_conversation([
        VMB1TS_module_info_exchange(module_address),
    ])

    req = generate_sanic_request()
    resp = await module_req(req, f'{module_address:02x}', '/type')
    mock_velbus.assert_conversation_happened_exactly()

    assert 200 == resp.status
    assert f'VMB1TS at 0x{module_address:02x}\r\n' == resp.body.decode('utf-8')


@pytest.mark.asyncio
async def test_VMB1TS_temperature(generate_sanic_request, module_address, mock_velbus):
    mock_velbus.set_expected_conversation([
        VMB1TS_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=SensorTemperatureRequest(),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=SensorTemperature(
                    current_temperature=22,
                ),
            ).to_bytes()
        ),
    ])

    req = generate_sanic_request()
    resp = await module_req(req, f'{module_address:02x}', '/temperature')
    mock_velbus.assert_conversation_happened_exactly()

    assert 200 == resp.status
    assert f'22.0' == resp.body.decode('utf-8')


@pytest.mark.asyncio
async def test_VMB1TS_cached_temperature(generate_sanic_request, module_address, mock_velbus):
    mock_velbus.set_expected_conversation([
        VMB1TS_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=SensorTemperatureRequest(),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=SensorTemperature(
                    current_temperature=23,
                ),
            ).to_bytes()
        ),
        (
            VelbusFrame(
                address=module_address,
                message=SensorTemperatureRequest(),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=SensorTemperature(
                    current_temperature=24,
                ),
            ).to_bytes()
        ),
        (
            VelbusFrame(
                address=module_address,
                message=SensorTemperatureRequest(),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=SensorTemperature(
                    current_temperature=25,
                ),
            ).to_bytes()
        ),
    ])

    with freeze_time() as frozen_datetime:
        req = generate_sanic_request()
        await module_req(req, f'{module_address:02x}', '/temperature')

        resp = await module_req(req, f'{module_address:02x}', '/temperature')
        # Should *not* re-request the temperature
        # Should still return the "old" 23ºC
        assert 200 == resp.status
        assert f'23.0' == resp.body.decode('utf-8')

        frozen_datetime.tick(delta=datetime.timedelta(seconds=15))

        resp = await module_req(req, f'{module_address:02x}', '/temperature')
        # Should *not* re-request the temperature
        # Should still return the "old" 23ºC
        assert 200 == resp.status
        assert f'23.0' == resp.body.decode('utf-8')

        req.headers = {
            "Cache-Control": "max-age=30",
        }
        resp = await module_req(req, f'{module_address:02x}', '/temperature')
        # Should *not* re-request the temperature
        # Should still return the "old" 23ºC
        assert 200 == resp.status
        assert f'23.0' == resp.body.decode('utf-8')

        req.headers = {
            "Cache-Control": "max-age=10",
        }
        resp = await module_req(req, f'{module_address:02x}', '/temperature')
        # *Should* re-request the temperature
        assert 200 == resp.status
        assert f'24.0' == resp.body.decode('utf-8')

        frozen_datetime.tick(delta=datetime.timedelta(seconds=61))

        req.headers = {}
        resp = await module_req(req, f'{module_address:02x}', '/temperature')
        # *Should* re-request the temperature
        assert 200 == resp.status
        assert f'25.0' == resp.body.decode('utf-8')


@pytest.mark.asyncio
async def test_VMB1TS_heater(generate_sanic_request, module_address, mock_velbus):
    mock_velbus.set_expected_conversation([
        VMB1TS_module_info_exchange(module_address),
        (
            VelbusFrame(
                address=module_address,
                message=ModuleStatusRequest(),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=TemperatureSensorStatus(
                    heater=True,
                ),
            ).to_bytes()
        ),
    ])

    req = generate_sanic_request()
    resp = await module_req(req, f'{module_address:02x}', '/heater')
    mock_velbus.assert_conversation_happened_exactly()

    assert resp.status == 200
    assert resp.body.decode('utf-8') == 'true'


@pytest.mark.asyncio
async def test_VMB1TS_message(generate_sanic_request, module_address, mock_velbus):
    mock_velbus.set_expected_conversation([
        VMB1TS_module_info_exchange(module_address),
    ])

    req = generate_sanic_request()
    await module_req(req, f'{module_address:02x}', '/type')
    mock_velbus.assert_conversation_happened_exactly()

    message(VelbusFrame(
        address=module_address,
        message=PushButtonStatus(
            just_pressed=Bitmap(8)([True, False, False, False, False, False, False, False])
        ),
    ))

    resp = await module_req(req, f'{module_address:02x}', '/heater')
    assert resp.status == 200
    assert resp.body.decode('utf-8') == "true"

    message(VelbusFrame(
        address=module_address,
        message=PushButtonStatus(
            just_released=Bitmap(8)([True, False, False, False, False, False, False, False])
        ),
    ))

    resp = await module_req(req, f'{module_address:02x}', '/heater')
    assert resp.status == 200
    assert resp.body.decode('utf-8') == "false"
