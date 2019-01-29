import re
import typing
from typing import Callable, Union, Awaitable

import sanic.response
import sanic.request

from ..VelbusProtocol import VelbusProtocol
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.ModuleInfo.ModuleInfo import ModuleInfo
from ..JsonPatchDict import JsonPatchDict


class VelbusModule():
    def __init__(self,
                 bus: VelbusProtocol,
                 address: int,
                 module_info: ModuleInfo = None,
                 update_state_cb: Callable = lambda ops: None):
        """
        Initialize module handling for the given address

        SubClasses do not need to call this __init__ method if they don't need
        its functionality. You will probably need to overload the self.state
        property in that case.

        :param bus: bus to communicate over to initialize the module further.
                    DO NOT STORE THIS VALUE, use the bus provided in dispatch()
                    to log the actual client making the requests (instead of
                    the client triggering the instantiation of this module)
        :param address: address of the module
        :param module_info: module info received in the ModuleType message
        :param update_state_cb: Callback to call with updates to state on the client
            Call signature: cb(ops: JsonPatch)
        :raises ValueError if this class is unwilling to handle the given address/module_info
        """
        self.address = address

        self._state = JsonPatchDict()
        self._state.callback.add(update_state_cb)
        # state is synced via WebSockets to JavaScript clients
        # You can use it as a nested dict. Be aware that Javascript requires strings as keys!
        #
        # It is advisable to keep the structure of `state` and the
        # URL-structure as similar as possible

    @property
    def state(self) -> typing.Dict:
        return self._state

    @state.setter
    def state(self, value) -> None:
        self._state.replace(value)

    def message(self, vbm: VelbusFrame) -> None:
        """
        A VelbusFrame from/to this module is seen.

        The class should update its state.

        :param vbm: The message
        """
        pass

    def lookup_method(self, path_info: str, method: str) -> Callable:
        method_name = '{}_{}'.format(path_info, method.upper())
        return getattr(self, method_name)  # may raise AttributeERror

    def dispatch(self,
                 path_info: str,
                 request: sanic.request,
                 bus: VelbusProtocol
                 ) -> Union[sanic.response.HTTPResponse, Awaitable[sanic.response.HTTPResponse]]:
        """
        HTTP calls are passed to this method.

        The default implementation uses the first component of the path
        as method name, followed by an underscore, followed by the HTTP
        method (in ALL CAPS).
        e.g. GET /module/01/test/foobar
        will call
             module_at_address_01.test_GET('/foobar', request, bus)

        :param path_info: Remaining components of the URI after the module address
                          (if any). Starts with a '/' if it's not empty
        :param request: Full request object to examine
        :param bus: to communicate with the Velbus
        :return: sanic.response or an awaitable returning one
        """
        if path_info == '':
            path_info = '/'

        module_path = path_info[1:].split('/', 1)  # skip leading /
        if len(module_path) == 1:
            module_path.append('')

        try:
            return self.lookup_method(module_path[0], request.method)(
                path_info=module_path[1],
                request=request,
                bus=bus,
            )
        except AttributeError:
            return sanic.response.text('Method not found\r\n', status=404)

    def _GET(self,
             path_info: str,
             request: sanic.request,
             bus: VelbusProtocol,
             *args, **kwargs
             ) -> Union[sanic.response.HTTPResponse, Awaitable[sanic.response.HTTPResponse]]:
        del request, bus, args, kwargs  # unused

        if path_info != '':
            return sanic.response.text('Not found\r\n', status=404)

        # Gerenate index
        paths = set()
        for path in dir(self):
            if path.startswith('_'):
                continue
            match = re.match(r'(.+)_([A-Z]+)', path)
            if not match:
                continue
            paths.add(match.group(1))

        return sanic.response.text('\r\n'.join(sorted(paths)) + '\r\n')

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
            "{} at 0x{:02x}\r\n".format(self.__class__.__name__, self.address)
        )
