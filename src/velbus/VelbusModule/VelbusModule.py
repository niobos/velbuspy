import asyncio
import dataclasses
import datetime
import functools
import inspect
import re
import typing
from typing import Callable, Union, Awaitable

import dateutil.parser
import sanic.response
import sanic.request
import sortedcontainers

from ..VelbusProtocol import VelbusProtocol
from ..VelbusMessage.VelbusFrame import VelbusFrame
from ..VelbusMessage.ModuleInfo.ModuleInfo import ModuleInfo
from ..JsonPatchDict import JsonPatchDict


@dataclasses.dataclass()
@functools.total_ordering
class DelayedCall:
    """
    Base class for delayed calls. Subclass this to include additional attributes

    `when` is either None (to indicate right away), or a datetime object. The constructor
    also accepts a string (which is passed through `datetime.parser.parse()`, or an integer/float
    indicating that many seconds from now.
    """
    when: datetime.datetime = None
    future: asyncio.Future = dataclasses.field(default=None, init=False, repr=False, hash=False)

    def __post_init__(self):
        self.future = asyncio.get_event_loop().create_future()

        if isinstance(self.when, datetime.datetime):
            pass
        elif self.when is None:
            pass
        elif isinstance(self.when, str):
            self.when = dateutil.parser.parse(self.when)
        elif isinstance(self.when, int) or isinstance(self.when, float):
            self.when = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=self.when)
        else:
            raise TypeError(f"Unrecognized type for `when`: {type(self.when)}")

        if self.when is not None and self.when.tzinfo is None:
            self.when = self.when.replace(tzinfo=datetime.timezone.utc)

    @classmethod
    def from_any(cls, o: typing.Any):
        """
        To override: convert basic types into cls()
        """
        return cls()

    def seconds_from_now(self, now: datetime.datetime = None):
        if self.when is None:
            return 0

        if now is None:
            now = datetime.datetime.now(tz=datetime.timezone.utc)
        if now.tzinfo is None:
            # assume UTC
            now = now.replace(tzinfo=datetime.timezone.utc)

        delta = self.when - now
        return delta.total_seconds()

    def as_dict(self) -> dict:
        ret = {}
        fields = dataclasses.fields(self)
        for field in fields:
            if field.repr:
                ret[field.name] = getattr(self, field.name)

        if self.when is None:
            ret['when'] = None
        else:
            ret['when'] = self.when.isoformat()
        return ret

    def __eq__(self, other):
        if not isinstance(other, DelayedCall):
            return False
        return self.when == other.when

    def __gt__(self, other):
        if not isinstance(other, DelayedCall):
            raise TypeError(f"Can't compare DelayedCall with {type(other)}")
        if self.when is None:
            return False  # None is always less than other
        if other.when is None:
            return True  # None is always less than self
        return self.when > other.when

    @classmethod
    def to_list(cls, o: typing.Any) -> typing.List["DelayedCall"]:  # TODO
        """
        Upgrades a (list of) dicts to a list of `cls`
        :raises TypeError if the conversion couldn't be done
        """
        if not isinstance(o, list):
            o = [o]

        ret = []
        for step in o:
            if isinstance(step, cls):
                ret.append(step)
            else:
                ret.append(cls.from_any(step))  # may raise
        return ret

    @staticmethod
    def is_trivial(steps: typing.List["DelayedCall"]) -> bool:
        return len(steps) == 1 and steps[0].when is None


class VelbusModule:
    def __init__(self,
                 bus: VelbusProtocol,
                 address: int,
                 module_info: ModuleInfo = None):
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
        # state is synced to MQTT and via WebSockets to JavaScript clients
        # You can use it as a nested dict. Be aware that Javascript requires strings as keys!
        #
        # It is advisable to keep the structure of `state` and the
        # URL-structure as similar as possible

        self._process_queue = sortedcontainers.SortedList()
        self._next_delayed_call: typing.Optional[asyncio.TimerHandle] = None

    @property
    def state(self) -> typing.Dict:
        return self._state

    @state.setter
    def state(self, value) -> None:
        self._state.replace(value)

    @property
    def state_callback(self) -> typing.Set:
        return self._state.callback

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

    def delayed_call(self, call_info: DelayedCall) -> typing.Any:
        """
        Function called after a delay.
        If it returns an awaitable (or is an async function), it is awaited for
        """
        raise NotImplementedError("Must be overridden")

    def _delayed_call(self) -> None:
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        while len(self._process_queue) and self._process_queue[0].seconds_from_now(now) <= 0:
            call_info = self._process_queue.pop(0)
            response = self.delayed_call(call_info)
            if inspect.isawaitable(response):
                task = asyncio.get_event_loop().create_task(response)
                task.add_done_callback(lambda result: call_info.future.set_result(result))
            else:
                call_info.future.set_result(response)

        self._schedule_next_delayed_call()

    def _schedule_next_delayed_call(self) -> None:
        if self._next_delayed_call is not None:
            self._next_delayed_call.cancel()
            self._next_delayed_call = None

        if len(self._process_queue) == 0:
            return

        delay = self._process_queue[0].seconds_from_now()
        self._next_delayed_call = asyncio.get_event_loop().call_later(delay, self._delayed_call)

    @property
    def delayed_calls(self) -> typing.List[DelayedCall]:
        return self._process_queue

    @delayed_calls.setter
    def delayed_calls(self, value: typing.Iterable[DelayedCall]):
        self._process_queue.clear()
        for call in value:
            self._process_queue.add(call)

        self._schedule_next_delayed_call()

    def delayed_calls_GET(self,
                          path_info: str,
                          *args, **kwargs,
                          ) -> sanic.response.HTTPResponse:
        if path_info != '':
            return sanic.response.text('Not found', status=404)

        return sanic.response.json([
            call.as_dict()
            for call in self.delayed_calls
        ])
