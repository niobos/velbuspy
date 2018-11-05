"""
Shared fixtures for use in tests
"""
import asyncio
import weakref
from typing import List, Union, Callable, Tuple

import pytest
import sanic.request

from velbus import HttpApi
from velbus.VelbusProtocol import VelbusProtocol, VelbusSerialProtocol


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
                conversation: List[Tuple[Union[bytes, Callable], Union[bytes, None]]]
        ):
            """
            Specify the expected conversation.
            :param conversation: A list of 2-tuples. Each tuple contains an expected message, and a response to be
            generated for that message.
            The message is either an exact byte sequence to match,
            or a callable that checks (probably in a more fuzzy way) the received bytes and returns the result.
            The response is either an exact byte sequence, or None, indicating no response needs to be generated.
            """
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
