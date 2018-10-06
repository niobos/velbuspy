import attr

from ._registry import register
from .ModuleInfo import ModuleInfo
from .._types import Enum, Bitmap, UInt


@register
@attr.s(slots=True, auto_attribs=True)
class VMB6IN(ModuleInfo):
    class ModuleType(Enum(8)):
        VMB6IN = 0x05
    _module_type: ModuleType = ModuleType.VMB6IN

    leds_on: Bitmap(8) = Bitmap(8).zero()
    leds_slow_blink: Bitmap(8) = Bitmap(8).zero()
    leds_fast_blink: Bitmap(8) = Bitmap(8).zero()

    build_year: UInt(8) = 0
    build_week: UInt(8) = 0
