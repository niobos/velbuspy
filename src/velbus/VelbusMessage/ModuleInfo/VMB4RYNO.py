import attr

from ._registry import register
from .ModuleInfo import ModuleInfo
from .._types import Enum, UInt


@register
@attr.s(slots=True, auto_attribs=True)
class VMB4RYNO(ModuleInfo):
    class ModuleType(Enum(8)):
        VMB4RYNO = 0x11
    _module_type: ModuleType = ModuleType.VMB4RYNO

    serial: UInt(16) = 0
    memory_map_version: UInt(8) = 0
    build_year: UInt(8) = 0
    build_week: UInt(8) = 0
