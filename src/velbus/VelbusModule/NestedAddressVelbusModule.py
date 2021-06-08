import typing
import weakref
import enum

import sanic.response
import sanic.request

from typing import Any, Callable, Dict, Union, Awaitable, Iterable

from .VelbusModule import VelbusModule
from ..VelbusProtocol import VelbusProtocol
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.ModuleInfo.ModuleInfo import ModuleInfo


class NestedAddressVelbusModule(VelbusModule):
    def __init__(
            self,
            bus: VelbusProtocol,
            address: int,
            module_info: ModuleInfo,
            channels: Iterable[Any],
            channel_type: type,
            ):
        super().__init__(bus=bus,
                         address=address,
                         module_info=module_info)

        self.submodules = {}
        for channel in channels:
            self.submodules[channel] = channel_type(
                bus=bus,
                channel=channel,
                parent_module=self,
            )
            self.submodules[channel]._state = self.state[channel]

    def parse_address(self, address: str) -> Any:
        """
        Parse and validate the address field from a HTTP path.
        The default implementation converts the string to int and checks if
        it exists in self.addresses.

        :param address: string of the requested address
        :return: any object representing the address
        :raises: ValueError when the address is invalid
        """
        address = int(address)
        if address not in self.submodules:
            raise ValueError("Unknown address")
        return address

    def parse_channel(self, vbm: VelbusFrame) -> typing.Optional[int]:
        """
        Optionally overridable.
        Parse a message and identify for which channel it is destined, or None to
        broadcast to all channels.

        The default implementation checks for a `channel` attribute in the message,
        and routes based on its value.
        """
        if hasattr(vbm.message, 'channel'):
            return vbm.message.channel
        return None

    def message(self, vbm: VelbusFrame) -> None:
        """
        Optionally override to only pass messages to the correct submodule.

        This default implementation tries to do this naively
        """
        to_channel = self.parse_channel(vbm)
        if to_channel is not None:
            self.submodules[to_channel].message(vbm)
        else:
            for submodule in self.submodules.values():
                submodule.message(vbm)

    def dispatch(self, path_info: str, request: sanic.request, bus: VelbusProtocol):
        """
        HTTP calls are passed to this method.

        This implementation uses the first component of the path as a (sub)address.
        The second component is handled as in VelbusModule.dispatch:
        as a method name, followed by an underscore, followed by the HTTP
        method (in ALL CAPS).

        e.g. GET /module/01/1/test/foobar
        will call
             module_at_address_01.test_GET(
                subaddress=1,
                path_info='/foobar',
                request=request,
                bus=bus)
        """
        if path_info == '':
            path_info = '/'

        if path_info == '/':
            # generate index
            addr_list = [str(_) for _ in self.submodules.keys()]
            addr_list.append('type')
            return sanic.response.text('\r\n'.join(addr_list) + '\r\n')

        module_path = path_info[1:].split('/', 2)  # skip leading /

        subaddress = module_path.pop(0)

        if subaddress == 'type':
            return super().dispatch(path_info, request, bus)

        try:
            subaddress = self.parse_address(subaddress)
        except ValueError:
            return sanic.response.text('subaddress `{}` not found'.format(subaddress), status=404)

        if len(module_path) < 1:
            module_path.append('')

        if len(module_path) < 2:
            module_path.append('')
        else:
            module_path[1] = '/' + module_path[1]

        try:
            method = self.submodules[subaddress].lookup_method(
                module_path[0], request.method)
            return method(
                    path_info=module_path[1],
                    request=request,
                    bus=bus,
                )
        except AttributeError:
            return sanic.response.text('{m} for {t} not found\r\n'.format(
                m=module_path[0],
                t=self.__class__.__name__,
            ),
                status=404
            )


class VelbusModuleChannel(VelbusModule):
    def __init__(self,
                 bus: VelbusProtocol,
                 channel: int,
                 parent_module: VelbusModule,
                 ):
        super().__init__(
            bus=bus,
            address=parent_module.address,
        )
        self.channel = channel
        self.parent = weakref.proxy(parent_module)  # avoid circular dependencies

    def type_GET(self,
                 path_info: str,
                 request: sanic.request,
                 bus: VelbusProtocol,
                 *args, **kwargs
                 ) -> Union[sanic.response.HTTPResponse, Awaitable[sanic.response.HTTPResponse]]:
        del request, bus, args, kwargs  # unused

        if path_info != '':
            return sanic.response.text('Not found\r\n', status=404)

        return sanic.response.text(
            f"{self.__class__.__name__} at 0x{self.address:02x}/{self.channel}\r\n"
        )
