import attr

from .VelbusMessage import VelbusMessage


@attr.s(slots=True, auto_attribs=True)
class UnknownMessage(VelbusMessage):
    _data: bytes = b''

    def data(self) -> bytes:
        return self._data
