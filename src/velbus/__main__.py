import argparse
import logging
import signal
import time
import asyncio

import datetime

import os
import serial
import serial_asyncio

from sanic import Sanic
import sanic.response

from .VelbusMessage.VelbusFrame import VelbusFrame
from .VelbusMessage.InterfaceStatusRequest import InterfaceStatusRequest
from .VelbusProtocol import VelbusProtocol, VelbusSerialProtocol, VelbusTcpProtocol, format_sockaddr
from .CachedException import CachedTimeoutError
from . import HttpApi

from .VelbusMessage._registry import command_registry
from .VelbusMessage.ModuleInfo._registry import module_type_registry

__import__('VelbusModule', globals(), level=1, fromlist=['*'])
# ^^^ from .VelbusModule import *    , but without polluting the namespace
from .VelbusModule._registry import module_registry


parser = argparse.ArgumentParser(description='Velbus communication daemon')
parser.add_argument('--tcp-port', help="TCP port to listen on", type=int, default=8445)
parser.add_argument('--static-dir', help="Directory to serve under /static the API", type=str,
                    default='{}/static'.format(os.path.dirname(__file__)))
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

logger.info("Loaded ModuleType decoder for:")
for mod in sorted(module_type_registry.keys()):
    for cls in module_type_registry[mod]:
        logger.info(" - {mod:02x} {cls}".format(mod=mod, cls=cls.__name__))

logger.info("Loaded Module managers for:")
for name in sorted(module_registry.keys(), key=lambda t: t.__name__):
    for cls in module_registry[name]:
        logger.info(" - {mod} -> {handler}".format(mod=name.__name__, handler=cls.__name__))


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


# Start up Web server
app = Sanic(__name__, log_config={})
app.config.LOGO = None
httpserver = app.create_server(host="0.0.0.0", port=8080, return_asyncio_server=True)
asyncio.get_event_loop().create_task(httpserver)


logger.info("Serving /static from {}".format(args.static_dir))
app.static('/static', args.static_dir)


@app.route('/')
async def index(request):
    return sanic.response.redirect('/static/index.html')


@app.exception(CachedTimeoutError)
def cached_timeout(request, exception):
    return sanic.response.text("timeout waiting for response\r\n",
                               headers={
                                   'Date': exception.timestamp.strftime("%a, %d %b %y %T GMT"),
                                   'Age': int((datetime.datetime.utcnow() - exception.timestamp).total_seconds()),
                               },
                               status=504)

@app.exception(TimeoutError)
def timeout(request, exception):
    return sanic.response.text("timeout waiting for response\r\n",
                               status=504)


HttpApi.add_routes(bus=internal, app=app)


# Run loop
try:
    loop.run_forever()
except KeyboardInterrupt:
    logger.warning("SIGINT received, closing...")
    pass

tcpserver.close()
loop.run_until_complete(tcpserver.wait_closed())
loop.close()
