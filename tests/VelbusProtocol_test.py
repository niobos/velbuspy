import pytest

from velbus.VelbusProtocol import VelbusProtocol
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
from velbus.VelbusMessage.ModuleType import ModuleType
from velbus.VelbusMessage.ModuleInfo.VMB4RYNO import VMB4RYNO


@pytest.mark.asyncio
async def test_reply(mock_velbus, module_address):
    mock_velbus.set_expected_conversation([
        (
            VelbusFrame(
                address=module_address,
                message=ModuleTypeRequest(),
            ).to_bytes(),
            VelbusFrame(
                address=module_address,
                message=ModuleType(
                    module_info=VMB4RYNO(),
                ),
            ).to_bytes()
        )
    ])
    bus = VelbusProtocol()
    bus.client_id = "INTERNAL"
    await bus.velbus_query(
        VelbusFrame(
            address=module_address,
            message=ModuleTypeRequest(),
        ),
        ModuleType,
    )


@pytest.mark.asyncio
async def test_no_reply(mock_velbus):
    mock_velbus.set_expected_conversation([
        (
            VelbusFrame(
                address=0x01,
                message=ModuleTypeRequest(),
            ).to_bytes(),
            VelbusFrame(
                address=0x01,
                message=ModuleType(
                    module_info=VMB4RYNO(),
                ),
            ).to_bytes()
        ),
    ])
    bus = VelbusProtocol()
    bus.client_id = "INTERNAL"

    with pytest.raises(TimeoutError):
        await bus.velbus_query(
            VelbusFrame(
                address=0x02,
                message=ModuleTypeRequest(),
            ),
            ModuleType,
            timeout=0.01,
        )
