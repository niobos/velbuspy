import attr

from ._registry import register
from .ModuleInfo import ModuleInfo
from .._types import Enum, UInt, BlindTimeout


@register
@attr.s(slots=True, auto_attribs=True)
class VMB2BL(ModuleInfo):
    class ModuleType(Enum(8)):
        VMB2BL = 0x09
    _module_type: ModuleType = ModuleType.VMB2BL

    _reserved: UInt(4) = 0
    timeout_blind2: BlindTimeout = BlindTimeout.t15sec
    timeout_blind1: BlindTimeout = BlindTimeout.t15sec

    build_year: UInt(8) = 0
    build_week: UInt(8) = 0
