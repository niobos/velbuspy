import pytest
import datetime
from freezegun import freeze_time

from velbus.HttpApi import module_req, message
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
from velbus.VelbusMessage.ModuleType import ModuleType
from velbus.VelbusMessage.ModuleInfo.VMB2BL import VMB2BL as VMB2BL_mi
from velbus.VelbusMessage.ModuleStatusRequest import ModuleStatusRequest
from velbus.VelbusMessage._types import BlindNumber
from velbus.VelbusMessage.BlindStatus import BlindStatusV1
from velbus.VelbusModule.VMB2BL import VMB2BL


_ = VMB2BL  # dummy usage to force import
# import needed to auto-register the module for processing


@pytest.mark.asyncio
async def test_VMB2BL_instantiation(generate_sanic_request, module_address, mock_velbus):
    mock_velbus.set_expected_conversation([
        (
            VelbusFrame(
                address=module_address,
                message=ModuleTypeRequest(),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=ModuleType(
                    module_info=VMB2BL_mi(),
                ),
            ).to_bytes()
        ),
    ])

    req = generate_sanic_request()
    resp = await module_req(req, f'{module_address:02x}', '/type')
    mock_velbus.assert_conversation_happened_exactly()

    assert 200 == resp.status
    assert f'VMB2BL at 0x{module_address:02x}\r\n' == resp.body.decode('utf-8')


@pytest.mark.asyncio
async def test_VMB2BL_status_position_estimation(generate_sanic_request, mock_velbus):
    mock_velbus.set_expected_conversation([
        (
            VelbusFrame(
                address=0x11,
                message=ModuleTypeRequest(),
            ).to_bytes(),
            VelbusFrame(
                address=0x11,
                message=ModuleType(
                    module_info=VMB2BL_mi(),
                ),
            ).to_bytes()
        ),
        (
            VelbusFrame(
                address=0x11,
                message=ModuleStatusRequest(
                    channel=1
                )
            ).to_bytes(),
            VelbusFrame(
                address=0x11,
                message=BlindStatusV1(
                    channel=BlindNumber(1),
                    blind_status=BlindStatusV1.BlindStatus.Off,
                ),
            ).to_bytes()
        ),
    ])

    with freeze_time() as frozen_datetime:
        req = generate_sanic_request()
        resp = await module_req(req, '11', '/1/position')

        mock_velbus.assert_conversation_happened_exactly()

        assert 200 == resp.status
        assert '50' == resp.body.decode('utf-8')

        message(VelbusFrame(
            address=0x11,
            message=BlindStatusV1(
                channel=BlindNumber(1),
                blind_status=BlindStatusV1.BlindStatus.Blind1Down,
            ),
        ))

        frozen_datetime.tick(delta=datetime.timedelta(seconds=15))

        message(VelbusFrame(
            address=0x11,
            message=BlindStatusV1(
                channel=BlindNumber(1),
                blind_status=BlindStatusV1.BlindStatus.Off,
            ),
        ))

        req = generate_sanic_request()
        resp = await module_req(req, '11', '/1/position')
        assert 200 == resp.status
        assert '100' == resp.body.decode('utf-8')

        message(VelbusFrame(
            address=0x11,
            message=BlindStatusV1(
                channel=BlindNumber(1),
                blind_status=BlindStatusV1.BlindStatus.Blind1Up,
            ),
        ))

        frozen_datetime.tick(delta=datetime.timedelta(seconds=3))

        message(VelbusFrame(
            address=0x11,
            message=BlindStatusV1(
                channel=BlindNumber(1),
                blind_status=BlindStatusV1.BlindStatus.Off,
            ),
        ))

        req = generate_sanic_request()
        resp = await module_req(req, '11', '/1/position')
        assert 200 == resp.status
        assert 80. == float(resp.body.decode('utf-8'))
