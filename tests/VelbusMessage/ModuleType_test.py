import json

from velbus.VelbusMessage.ModuleInfo.VMB2BL import VMB2BL
from velbus.VelbusMessage.VelbusFrame import VelbusFrame
from velbus.VelbusMessage.ModuleType import ModuleType
from velbus.VelbusMessage.ModuleInfo.UnknownModuleInfo import UnknownModuleInfo
from velbus.VelbusMessage.ModuleInfo.VMB4RYNO import VMB4RYNO
from velbus.VelbusMessage.ModuleInfo.VMBGPOD import VMBGPOD
from velbus.VelbusMessage._types import BlindTimeout


def test_decode_unknown():
    b = b'\x0f\xfb\x73\x07\xff\xff\x8b\xa4\x01\x16\x12\x26\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == ModuleType(
        module_info=UnknownModuleInfo(
            data=b'\xff\x8b\xa4\x01\x16\x12'))

    assert json.dumps(a.to_json_able())


def test_decode_VMB4RYNO():
    b = b'\x0f\xfb\x00\x07\xff\x11\x00\x00\x00\x00\x00\xdf\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == ModuleType(
        module_info=VMB4RYNO()
    )

    assert json.dumps(a.to_json_able())


def test_decode_VMBGPOD():
    b = b'\x0f\xfb\x00\x07\xff\x28\x00\x00\x00\x00\x00\xc8\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == ModuleType(
        module_info=VMBGPOD())

    assert json.dumps(a.to_json_able())


def test_decode_VMB2BL():
    b = b'\x0f\xfb\x2b\x05\xff\x09\x05\x08\x15\x9c\x04'
    a = VelbusFrame.from_bytes(b)
    assert a.to_bytes() == b

    assert a.message == ModuleType(
        module_info=VMB2BL(
            timeout_blind1=BlindTimeout.t30sec,
            timeout_blind2=BlindTimeout.t30sec,
            build_year=8, build_week=21,
        ))

    assert json.dumps(a.to_json_able())
