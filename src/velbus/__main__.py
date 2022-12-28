import argparse
import logging
import signal
import time
import asyncio

import serial
import serial_asyncio

from .VelbusMessage.VelbusFrame import VelbusFrame
from .VelbusMessage.InterfaceStatusRequest import InterfaceStatusRequest
from .VelbusProtocol import VelbusProtocol, VelbusSerialProtocol, VelbusTcpProtocol, format_sockaddr

from .VelbusMessage._registry import command_registry


parser = argparse.ArgumentParser(
    description='Velbus communication daemon',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument('--tcp-port', help="TCP port to listen on", type=int, default=8445)
parser.add_argument('--logfile', help="Log to the given file", type=str)
parser.add_argument('--debug', help="Enable debug mode", action='store_true')
parser.add_argument('serial_port', help="Serial port to open")

args = parser.parse_args()


logging.getLogger(None).setLevel(logging.INFO)
logging.Formatter.converter = time.gmtime

if args.debug:
    # load all decoders
    __import__('VelbusMessage', globals(), level=1, fromlist=['*'])

    logging.getLogger(None).setLevel(logging.DEBUG)

if args.logfile:
    log_file_handler = logging.FileHandler(args.logfile)
else:
    log_file_handler = logging.StreamHandler()
log_file_handler.setFormatter(logging.Formatter(
    fmt="%(asctime)sZ [%(name)s %(levelname)s] %(message)s"
))
logging.getLogger(None).addHandler(log_file_handler)


logger = logging.getLogger(__name__)


# Print loaded modules
logger.info("Loaded VelbusMessage decoder for:")
for cmd in sorted(command_registry.keys()):
    for cls in command_registry[cmd]:
        logger.info(" - 0x{cmd:02x} {cls}".format(cmd=cmd, cls=cls.__name__))


loop = asyncio.get_event_loop()

def handle_sighup():
    logger.info("Received SIGHUP, reopening log file")
    log_file_handler.close()
    logger.info("Received SIGHUP, log file reopened")

loop.add_signal_handler(signal.SIGHUP, handle_sighup)

# Connect to serial port
serial_transport, serial_protocol = loop.run_until_complete(
    serial_asyncio.create_serial_connection(
        loop, VelbusSerialProtocol, args.serial_port,
        baudrate=38400,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
    ))
try:
    logger.debug("Old DTR/RTS: {}/{}".format(
        serial_transport._serial.dtr,
        serial_transport._serial.rts
    ))
    serial_transport._serial.dtr = False  # low
    serial_transport._serial.rts = True   # high
    logger.debug("New DTR/RTS: {}/{}".format(
        serial_transport._serial.dtr,
        serial_transport._serial.rts
    ))
except OSError as e:
    logger.warning("Could not set DTR/RTS status, trying anyway... ({})".format(str(e)))

# send an interface status request, so we can quit right away if the bus is not active
internal = VelbusProtocol(client_id="INTERNAL")
loop.run_until_complete(internal.process_message(VelbusFrame(address=0, message=InterfaceStatusRequest())))
# The reply will be read as soon as we enter the loop


# Start up TCP server
tcpserver = loop.run_until_complete(
    loop.create_server(VelbusTcpProtocol, None, args.tcp_port, reuse_port=True))
logger.info("Listening for TCP on {}".format(
    format_sockaddr(tcpserver.sockets[0].getsockname())))

# Run loop
try:
    loop.run_forever()
except KeyboardInterrupt:
    logger.warning("SIGINT received, closing...")
    pass

tcpserver.close()
loop.run_until_complete(tcpserver.wait_closed())
loop.close()
