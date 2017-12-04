import attr

from ._registry import register
from .ModuleInfo import ModuleInfo
from .._types import Enum, UInt


@register
@attr.s(slots=True, auto_attribs=True)
class VMB1TS(ModuleInfo):
    class ModuleType(Enum(8)):
        VMB1TS = 0x0c
    _module_type: ModuleType = ModuleType.VMB1TS

    zone_number: UInt(8) = 0
    build_year: UInt(8) = 0
    build_week: UInt(8) = 0
