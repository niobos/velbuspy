import attr

from ._registry import register
from .VelbusMessage import VelbusMessage
from ._types import Enum, UInt
from .ModuleInfo.ModuleInfo import ModuleInfo
from .ModuleInfo._registry import module_type_registry
from .ModuleInfo.UnknownModuleInfo import UnknownModuleInfo


@register
@attr.s(slots=True, auto_attribs=True)
class ModuleType(VelbusMessage):
    _priority: UInt(2) = 3

    class Command(Enum(8)):
        ModuleType = 0xff
    _command: Command = Command.ModuleType

    module_info: ModuleInfo = UnknownModuleInfo()

    @classmethod
    def from_bytes(cls, data, *args, **kwargs) -> 'VelbusMessage':
        """
        Factory method that gets partially parsed bytes (in kwargs and data).
        Further parse data and return appropriate VelbusMessage object
        """
        if len(data) < 2:
            raise ValueError("Message not long enough")

        cmd = cls.Command(data[0])
        module_info = data[1:]

        try:
            try:
                candidates = module_type_registry[module_info[0]]
            except KeyError:
                raise ValueError()

            for c in candidates:
                try:
                    module_info = c.from_bytes(
                        data=module_info,
                    )
                    break
                except ValueError:
                    pass

            if not isinstance(module_info, ModuleInfo):
                raise ValueError()

        except ValueError:
            module_info = UnknownModuleInfo.from_bytes(data=module_info)

        kwargs['command'] = cmd
        kwargs['module_info'] = module_info
        return cls(*args, **kwargs)

    def data(self) -> bytes:
        return bytes([self._command.value]) + self.module_info.data()

    def validate(self):
        # TODO
        pass

    def to_json_able(self):
        return self.module_info.to_json_able()
