import attr

from ._registry import register
from .ModuleInfo import ModuleInfo
from .._types import Enum, UInt


@register
@attr.s(slots=True, auto_attribs=True)
class VMBGPOD(ModuleInfo):
    class ModuleType(Enum(8)):
        VMBGPOD = 0x28
    _module_type: ModuleType = ModuleType.VMBGPOD

    serial: UInt(16) = 0
    memory_map_version: UInt(8) = 0
    build_year: UInt(8) = 0
    build_week: UInt(8) = 0
