import attr

from .ModuleInfo import ModuleInfo


@attr.s(slots=True, auto_attribs=True)
class UnknownModuleInfo(ModuleInfo):
    _data: bytes = b''

    @classmethod
    def from_bytes(cls, data, *args, **kwargs):
        return cls(data=data, *args, **kwargs)

    def data(self) -> bytes:
        return self._data
