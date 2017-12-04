import attr
from .._utils import bytes_to_attrs, attrs_to_bytes, AttrSerializer


@attr.s(slots=True)
class ModuleInfo(AttrSerializer):
    pass
