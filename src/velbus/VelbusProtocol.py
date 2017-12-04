import asyncio
import concurrent
import inspect
import logging

from .VelbusMessage.VelbusFrame import VelbusFrame
from .VelbusMessage.BusActive import BusActive
from .VelbusMessage.BusOff import BusOff
from .VelbusMessage.RxBufFull import RxBufFull
from .VelbusMessage.RxBufReady import RxBufReady


logger = logging.getLogger(__name__)


def format_sockaddr(sockaddr):
    if len(sockaddr) == 4:  # IPv6
        return "[{h}]:{p}".format(
            h=sockaddr[0],
            p=sockaddr[1],
        )
    elif len(sockaddr) == 2:  # IPv4
        return "{h}:{p}".format(
            h=sockaddr[0],
            p=sockaddr[1],
        )
    else:
        raise TypeError("Unknown sockaddr format: {}".format(sockaddr))


class VelbusProtocol(asyncio.Protocol):
    serial_client: 'VelbusProtocol' = None
    tcp_clients: 'Set[VelbusProtocol]' = set()
    listeners = set()

    def connection_made(self, transport):
        self.transport = transport
        self.rx_buf = bytearray()
        logger.info("{p} : new connection".format(
            p=self.client_id
        ))

    def connection_lost(self, exc):
        logger.info("{cid} : connection closed{dr}".format(
            cid=self.client_id,
            dr=" with {} bytes unparsed".format(len(self.rx_buf)) if self.rx_buf else "",
        ))

    def data_received(self, data: bytearray):
        logger.debug("{cid} : Buf=[{b}], Rx=[{d}]".format(
            cid=self.client_id,
            b=' '.join(["{:02x}".format(b) for b in self.rx_buf]),
            d=' '.join(["{:02x}".format(b) for b in data])
        ))
        self.rx_buf.extend(data)
        self.try_decode()

    def try_decode(self):
        while self.rx_buf:
            try:
                vbm = VelbusFrame.from_bytes(self.rx_buf)

                self.process_message(vbm)

            except BufferError:
                break

            except ValueError as e:
                logger.warning("{cid} : Invalid message, discarding 1 byte (0x{b:02x}): {e}".format(
                    cid=self.client_id, b=self.rx_buf[0],
                    e=e,
                ))
                del self.rx_buf[0:1]
                continue

    def process_message(self, vbm: VelbusFrame):
        """
        Process a single message from this connection.
        This should usually relay the message, but you can filter messages here
        """
        logger.info("{cid} : VBM: [{m}]".format(
            cid=self.client_id,
            m=' '.join(['{:02x}'.format(b) for b in vbm.to_bytes()]),
        ))
        logger.debug("%s : VBM: %r", self.client_id, vbm)
        # ^^ don't use ''.format()
        # This allows the repr(vbm) call to be omitted if the message is discarded

        return self.relay_message(vbm)

    def relay_message(self, vbm: VelbusFrame):
        data = vbm.to_bytes()

        # Order of relaying logic:
        #  - Serial first. Serial is the slowest output. Send there first
        #    so by the time that the rest is sent, Serial is hopefully done by then
        #  - TCP next
        #  - listeners (potentially even async)

        if VelbusProtocol.serial_client != self:  # don't loop back
            VelbusProtocol.serial_client.transport.write(data)

        for c in VelbusProtocol.tcp_clients:
            if c != self:  # Don't loop back
                c.transport.write(data)

        for l in VelbusProtocol.listeners:
            _ = l(vbm)
            if inspect.isawaitable(_):
                asyncio.ensure_future(_)

    async def velbus_query(self,
                           question: VelbusFrame,
                           response_type: type,
                           response_address: int = None,
                           timeout: int = 2,
                           additional_check=(lambda vbm: True)):
        """
        Send a message on the bus and expect an answer

        :param question: The message to send (or None if nothing is to be sent)
        :param response_type: The type of message expected as response (probably a subclass of VelbusMessage)
        :param response_address: Override of the response address (defaults to the address the `question` is sent to)
        :param timeout: Timeout in seconds
        :param additional_check: Additional callable to filter the message
        :return: The message
        :raises: TimeoutError
        """
        if response_address is None:
            response_address = question.address

        reply = asyncio.get_event_loop().create_future()

        def message_filter(vbm: VelbusFrame):
            if vbm.address == response_address and \
                    isinstance(vbm.message, response_type) and \
                    additional_check(vbm):
                reply.set_result(vbm)

        self.listeners.add(message_filter)

        if question is not None:
            self.process_message(question)

        try:
            await asyncio.wait_for(reply, timeout)
            return reply.result()
        except concurrent.futures._base.TimeoutError:
            raise TimeoutError
        finally:
            self.listeners.remove(message_filter)


class VelbusTcpProtocol(VelbusProtocol):
    def connection_made(self, transport):
        self.client_id = "TCP:" + format_sockaddr(transport.get_extra_info('peername'))
        super().connection_made(transport)
        VelbusProtocol.tcp_clients.add(self)
        if VelbusProtocol.serial_client.paused:
            asyncio.get_event_loop().call_soon(self.transport.pause_reading)
            # BUG: this doesn't seem to work if it is called right now:
            # The transport does report being paused (._paused == True), but data_received() is called anyway
            # Wrapping in a call_soon seems to solve this bug

    def connection_lost(self, exc):
        super().connection_lost(exc)
        VelbusProtocol.tcp_clients.remove(self)

    def pause_writing(self):
        logger.warning("{} : buffer full, dropping connection".format(
            self.client_id,
        ))
        self.transport.abort()


class VelbusSerialProtocol(VelbusProtocol):
    def connection_made(self, transport):
        VelbusProtocol.serial_client = self
        self.client_id = "SERIAL"
        self.paused = False
        super().connection_made(transport)

    def connection_lost(self, exc):
        super().connection_lost(exc)
        VelbusProtocol.serial_client = None
        asyncio.get_event_loop().stop()

    def process_message(self, vbm: VelbusFrame):
        if isinstance(vbm.message, RxBufFull):
            self.pause_writing()
        elif isinstance(vbm.message, RxBufReady):
            self.resume_writing()
        elif isinstance(vbm.message, BusOff):
            # we lost connectivity to the bus. Things may have changed beyond your imagination.
            logger.warning("{} : bus off, exitting...".format(self.client_id))
            asyncio.get_event_loop().stop()
            # TODO: make this better
        elif isinstance(vbm.message, BusActive):
            pass

        super().process_message(vbm)

    def pause_writing(self):
        logger.warning("{} : buffer full, pausing writes".format(
            self.client_id,
        ))
        self.paused = True
        for c in VelbusProtocol.tcp_clients:
            c.transport.pause_reading()
            c.transport.pause_reading()

    def resume_writing(self):
        logger.warning("{} : buffer OK, resuming writes".format(
            self.client_id,
        ))
        self.paused = False
        for c in VelbusProtocol.tcp_clients:
            c.transport.resume_reading()


class VelbusHttpProtocol(VelbusProtocol):
    def __init__(self, request):
        self.client_id = "HTTP:{ip_port}{path}".format(
            ip_port=format_sockaddr(request.ip),
            path=request.path
        )
