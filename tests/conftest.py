"""
Shared fixtures for use in tests
"""
import asyncio
import random
import typing
import inspect
import weakref

import attr
import pytest
import sanic.request

from velbus import HttpApi
from velbus.VelbusProtocol import VelbusProtocol, VelbusSerialProtocol
from velbus.VelbusMessage.VelbusFrame import VelbusFrame


@pytest.fixture
def clean_http_api(request):
    del request  # unused
    HttpApi.modules.clear()
    HttpApi.ws_clients.clear()
    yield
    # leave dirty


@pytest.fixture
def sanic_req(request):
    del request  # unused
    req = sanic.request.Request(b'/modules/01/', {}, 1.1, 'GET', None)
    req._socket = None
    req._ip = '127.0.0.1'
    req._port = 9
    return req


@pytest.fixture
def generate_sanic_request(request):
    del request  # unused

    def generator(
            path: str = '/',
            method: str = 'GET',
            body: str = '',
    ):
        req = sanic.request.Request(path.encode('utf-8'), {}, 1.1, method, None)
        req.body = body.encode('utf-8')
        req._socket = None
        req._ip = '127.0.0.1'
        req._port = '1337'
        return req

    return generator


@pytest.fixture(params=[0x01, 0x11])
def module_address(request):
    """
    Test different module addresses.
    Especially test the case where decimal & hex representations differ,
    and test leading 0's
    """
    return request.param


@pytest.fixture
def mock_velbus(request):
    del request  # unused

    class FakeTransport():
        def __init__(self, parent: "FakeSerialProtocol"):
            self.parent = weakref.proxy(parent)
            self.paused = False
            self.read_queue = list()

        def write(self, data):
            data = bytes(data)  # convert to bytes from bytearray

            # Is this the expected data?
            if len(self.parent.conversation_to_happen) == 0:
                data_is_expected = False
            else:
                next_conversation = self.parent.conversation_to_happen[0]

                if callable(next_conversation[0]):
                    data_is_expected = next_conversation[0](data)
                else:
                    data_is_expected = (data == next_conversation[0])

            if data_is_expected:
                next_conversation = self.parent.conversation_to_happen.pop(0)
                if next_conversation[1] is not None:
                    self.queue_read(next_conversation[1])
            else:
                self.parent.unexpected_messages.append(data)
                # don't answer

        def pause_reading(self):
            self.paused = True

        def resume_reading(self):
            self.paused = False
            while self.read_queue:
                data = self.read_queue.pop(0)
                asyncio.get_event_loop().create_task(
                    self.do_read(data)
                )

        def queue_read(self, data):
            if self.paused:
                self.read_queue.append(data)
            else:
                asyncio.get_event_loop().create_task(
                    self.do_read(data)
                )

        async def do_read(self, data):
            # TODO: Log?
            self.parent.data_received(data)

    class FakeSerialProtocol(VelbusSerialProtocol):
        def __init__(self):
            super().__init__()
            self.conversation_to_happen = list()
            self.unexpected_messages = list()

        def set_expected_conversation(
                self,
                conversation: typing.List[
                    typing.Tuple[
                        typing.Union[bytes, typing.Callable],
                        typing.Union[bytes, None]
                    ]]
        ):
            """
            Specify the expected conversation.
            :param conversation: A list of 2-tuples. Each tuple contains an expected message, and a response to be
            generated for that message.
            The message is either an exact byte sequence to match,
            or a callable that checks (probably in a more fuzzy way) the received bytes and returns the result.
            The response is either an exact byte sequence, or None, indicating no response needs to be generated.
            """
            # Validate input
            for index, exchange in enumerate(conversation):
                if not len(exchange) == 2:
                    raise ValueError("Invalid conversation, expected a list of tuples")
                if not isinstance(exchange[0], bytes) and not isinstance(exchange[0], bytearray) \
                        and not callable(exchange[0]):
                    raise ValueError(f"Invalid conversation, expected bytes or callable in exchange {index}, rx")
                if not isinstance(exchange[1], bytes) and not isinstance(exchange[1], bytearray) \
                        and not exchange[1] is None:
                    raise ValueError(f"Invalid conversation, expected bytes or None in exchange {index}, tx")

            self.conversation_to_happen = conversation

        def assert_conversation_happened(self) -> bool:
            return len(self.conversation_to_happen) == 0

        def assert_conversation_happened_exactly(self) -> bool:
            return self.assert_conversation_happened() \
                   and len(self.unexpected_messages) == 0

    VelbusProtocol.serial_client = FakeSerialProtocol()
    VelbusProtocol.serial_client.connection_made(FakeTransport(VelbusProtocol.serial_client))
    VelbusProtocol.serial_client.client_id = "FAKE_SERIAL"

    HttpApi.modules.clear()
    HttpApi.ws_clients.clear()
    VelbusProtocol.listeners = {HttpApi.message}

    yield VelbusProtocol.serial_client

    VelbusProtocol.serial_client = None
    HttpApi.modules.clear()
    HttpApi.ws_clients.clear()
    VelbusProtocol.listeners.clear()


@pytest.fixture(params=[0, 1])  # test with at least 2 values
def magic_str(request):
    start = 1E6 * request.param
    return str(random.randint(start, start + 1E6))


class FakeSleep:
    sleeping_coros = set()

    @attr.s(auto_attribs=True, hash=True)
    class Waiter:
        future: asyncio.Future
        calling_function_name: str
        timeout_handle: asyncio.Handle = None

    waiters_for_new_calls: typing.Set["FakeSleep.Waiter"] = set()

    def __init__(self, delay, result=None):
        self.delay = delay
        self.result = result
        self.shortcut = asyncio.get_event_loop().create_future()
        self._cancelled = False

        self.caller = inspect.stack()[1].function
        # print(f"New sleep({delay}) call from {self.caller} => {id(self)}")

        self.sleeping_coros.add(self)

        waiters_to_wake = set()
        for waiter in self.waiters_for_new_calls:
            if waiter.calling_function_name is None \
                    or waiter.calling_function_name == self.caller:
                waiters_to_wake.add(waiter)

        for waiter in waiters_to_wake:
            if not waiter.future.done():
                waiter.future.set_result(self)

    def return_asap(self) -> None:
        if not self.shortcut.done():
            self.shortcut.set_result(None)
        # else: already returned

    def cancelled(self) -> bool:
        return self._cancelled

    async def do_actual_sleep(self) -> typing.Any:
        try:
            await asyncio.wait_for(self.shortcut, self.delay)
        except asyncio.TimeoutError:
            pass
        except asyncio.CancelledError:
            self._cancelled = True
        finally:
            self.sleeping_coros.remove(self)
        return self.result

    def __await__(self) -> typing.Any:
        return self.do_actual_sleep().__await__()

    @classmethod
    def new_sleep_call(
            cls,
            from_function: str = None,
            timeout: typing.Union[float, None] = 1,
    ) -> typing.Awaitable["FakeSleep"]:
        waiter = FakeSleep.Waiter(
            future=asyncio.get_event_loop().create_future(),
            calling_function_name=from_function,
        )

        cls.waiters_for_new_calls.add(waiter)

        def cleanup_waiter(fut):
            cls.waiters_for_new_calls.remove(waiter)
        waiter.future.add_done_callback(cleanup_waiter)

        # print(f"Waiting for sleep() call to be called from {from_function}, waiter {id(waiter)}")

        if timeout is not None:
            def timeout_triggered():
                if not waiter.future.done():
                    waiter.future.set_exception(TimeoutError("No (matching) sleep() call seen"))
            waiter.timeout_handle = asyncio.get_event_loop().call_later(
                timeout, timeout_triggered)

        return waiter.future


@pytest.fixture()
def fake_asyncio_sleep(mocker):
    mocker.patch('asyncio.sleep', new=FakeSleep)
    yield FakeSleep
    mocker.stopall()
