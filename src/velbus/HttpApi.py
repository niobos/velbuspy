"""
The /module_state WebSocket interface
-------------------------------------

The module_state WebSocket interface allows you to get real-time notifications
about changes to the module state (at least, to the part of the module state
that the module considers important to expose to clients).

The protocol used is JSON Patch [RFC6902], updating an initially empty object
on the remote side with information.

The object maintained on the server (and thus controlled by the client) is a
dict[str, bool], keeping track of which address(es) the client wants to
receive updates for.
The client should start by adding `true` to the address(es) it is interested
in:
    [{'op': 'add', 'path': '/1f', 'value': true}]
Note that the addresses (in the path) are hex-encoded (just like the REST
URLs)
A client can remove his interest in a module by removing the path, or by
setting it to false.

The object maintained on the client (and thus controlled by the server) is
a dict[str,dict], mapping module addresses to the module state. The layout
is module-dependent, so it is advisable for the client to `GET
/module/1f/type` to make sense of the data.
The server will respond to an added interest by adding the current state
of the module:
    [{'op': 'add', 'path': '/1f', 'value': {}}]
And will send (unsollicited) updates when things change.
Setting the `null` value means the module was not found.

When the module is removed from the server, it is also removed from the client
The client can re-request a subscription if it wants to.
"""
import contextvars
import inspect
import json
import logging
import datetime
import asyncio
from typing import Dict, Awaitable, Callable, Union

import re
import sanic.response
import sanic.request
import websockets

from .CachedException import CachedTimeoutError
from .JsonPatchDict import JsonPatchOperation, JsonPatch
from .VelbusProtocol import VelbusProtocol, VelbusHttpProtocol, format_sockaddr

from .VelbusMessage.VelbusFrame import VelbusFrame
from .VelbusMessage.ModuleTypeRequest import ModuleTypeRequest
from .VelbusMessage.ModuleType import ModuleType

from .VelbusModule._registry import module_registry
from .VelbusModule.VelbusModule import VelbusModule
from .VelbusModule.UnknownModule import UnknownModule


modules: Dict[int, Union[asyncio.Future, Awaitable[VelbusModule]]] = dict()
ws_clients = set()

sanic_request = contextvars.ContextVar('sanic_request')
sanic_request_datetime = contextvars.ContextVar('sanic_request_datetime')


def timestamp(request: sanic.request) -> sanic.response:
    """
    Returns the current (server) timestamp.
    Useful to calibrate client-server time differences.
    """
    del request  # unused
    return sanic.response.text("{}\r\n".format(datetime.datetime.utcnow().timestamp()))


async def delete_modules(request: sanic.request) -> sanic.response:
    del request  # unused
    modules.clear()
    for ws in ws_clients:
        ws.subscribed_modules = set()
        await ws.send(json.dumps([{
            'op': 'replace',
            'path': '/',
            'value': {},
        }]))
    return sanic.response.text("Cache flushed\r\n")


async def delete_module(request: sanic.request, address: str) -> sanic.response:
    del request  # unused
    address = int(address, 16)
    if address in modules:
        del modules[address]
        for ws in ws_clients:
            if address in ws.subscribed_modules:
                await ws_client_unlisten_module(address, ws)
        return sanic.response.text("Deleted from cache\r\n")
    else:
        return sanic.response.text("Not in cache\r\n")


async def module_req(request: sanic.request, address: str, module_path: str) -> sanic.response:
    sanic_request.set(request)
    sanic_request_datetime.set(datetime.datetime.utcnow())

    address = int(address, 16)
    bus = VelbusHttpProtocol(request)
    mod = await get_module(bus, address)

    response = mod.dispatch(module_path, request, bus)
    if inspect.isawaitable(response):
        response = await response
    return response


async def module_state_ws(request: sanic.request, ws: websockets.protocol.WebSocketCommonProtocol):
    logger = logging.getLogger(__name__)

    client_id = format_sockaddr(ws.remote_address)
    logger.info("{p} : new WebSocket connection ({ua})".format(
        p=client_id,
        ua=request.headers['user-agent'],
    ))

    ws.subscribed_modules = set()

    ws_clients.add(ws)
    try:
        while True:
            msg = await ws.recv()
            await handle_ws_message(VelbusHttpProtocol(request), ws, msg)

    except ValueError as e:
        logger.warning("{p} : invalid message received, dropping client: {e}".format(
            p=client_id,
            e=e,
        ))
    except websockets.exceptions.ConnectionClosed:
        logger.info("{p} : WebSocket connection closed".format(
            p=client_id
        ))
    finally:
        ws_clients.remove(ws)


async def handle_ws_message(bus: VelbusHttpProtocol,
                            ws: websockets.protocol.WebSocketCommonProtocol,
                            msg):
    """
    Tries to handle message
    :param bus: bus to query over (to add new modules)
    :param msg: the raw received message
    :param ws: the websocket to handle on
    :raises: ValueError when the message is malformed
    """
    try:
        msg = json.loads(msg)
    except json.JSONDecodeError as e:
        raise ValueError("JSON decode failed") from e

    if not isinstance(msg, list):
        raise ValueError("Not a list")

    for op in msg:
        try:
            if not re.match(r'^/[0-9a-fA-F]{2}$', op['path']):
                raise ValueError("Path not supported")
            address = int(op['path'][1:3], 16)

            if op['op'] in ('add', 'replace'):
                if not isinstance(op['value'], bool):
                    raise ValueError("Value not supported")

                if op['value']:
                    await ws_client_listen_module(bus, address, ws)
                else:
                    await ws_client_unlisten_module(address, ws)

            elif op['op'] == 'remove':
                if 'value' in op:
                    raise ValueError("remove with value present")
                await ws_client_unlisten_module(address, ws)

            else:
                raise ValueError('op not supported')

        except KeyError as e:
            raise ValueError("Could not find required property") from e


async def ws_client_listen_module(bus: VelbusHttpProtocol,
                                  address: int,
                                  ws: websockets.protocol.WebSocketCommonProtocol):
    try:
        mod = await get_module(bus, address)

        ws.subscribed_modules.add(address)
        # possible race condition here
        mod_state = mod.state
        await ws.send(json.dumps(
            JsonPatch([
                JsonPatchOperation(
                    op=JsonPatchOperation.Operation.add,
                    path=['{:02x}'.format(address)],
                    value=mod_state)
                ]
            ).to_json_able()
        ))

    except TimeoutError:
        await ws.send(json.dumps(
            JsonPatch([
                JsonPatchOperation(
                    op=JsonPatchOperation.Operation.add,
                    path=['{:02x}'.format(address)],
                    value=None),
                ]
            ).to_json_able()
        ))


async def ws_client_unlisten_module(address: int, ws: websockets.protocol.WebSocketCommonProtocol):
    ws.subscribed_modules.remove(address)
    await ws.send(json.dumps(
        JsonPatch([
            JsonPatchOperation(
                op=JsonPatchOperation.Operation.remove,
                path=['{:02x}'.format(address)],
                value=None),
            ]
        ).to_json_able()
    ))


def add_routes(bus: VelbusProtocol, app: sanic.Sanic):
    bus.listeners.add(message)

    app.add_route(timestamp, '/timestamp', methods=['GET'])

    app.add_route(delete_modules, '/module', methods=['DELETE'])
    app.add_route(delete_module, '/module/<address:[0-9a-fA-F]{2}>', methods=['DELETE'])

    app.add_route(module_req, '/module/<address:[0-9a-fA-F]{2}><module_path:|/.*>',
                  # Explicitly mention `/` in the regex to force `.` to also match `/`
                  methods=['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE'])

    app.add_websocket_route(module_state_ws, '/module_state')


def message(vbm: VelbusFrame):
    try:
        mod = modules[vbm.address].result()
        return mod.message(vbm)  # May be an awaitable
    except (KeyError, asyncio.CancelledError, asyncio.InvalidStateError, TimeoutError):
        # module not loaded, get_module() was cancelled, is not done (yet) or resulted in a timeout
        # No module to send message to, ignore
        pass


def get_module(bus: VelbusProtocol, address: int) -> Awaitable[VelbusModule]:
    """
    Factory method for a module object. Either from cache, or freshly created

    :param bus: The bus to ask on
    :param address: address to create object for
    :return: A future resulting in the VelbusModule object of the correct type
    """
    if address not in modules:
        modules[address] = asyncio.ensure_future(get_module_fresh(bus, address))

    return modules[address]


def gen_update_state_cb(address) -> Callable:
    def update_state_cb(ops: JsonPatch):
        prefixed_ops = ops.prefixed(['{:02x}'.format(address)])
        json_patch = json.dumps(prefixed_ops.to_json_able())

        for ws in ws_clients:
            if address in ws.subscribed_modules:
                asyncio.ensure_future(ws.send(json_patch))
    return update_state_cb


async def get_module_fresh(bus: VelbusProtocol, address: int) -> VelbusModule:
    try:
        module_type = await bus.velbus_query(
            VelbusFrame(
                address=address,
                message=ModuleTypeRequest()
            ),
            ModuleType
        )
    except TimeoutError:
        raise CachedTimeoutError from TimeoutError
    module_type_cls = module_type.message.module_info.__class__

    try:
        try:
            candidates = module_registry[module_type_cls]
        except KeyError:
            raise ValueError()

        for c in candidates:
            try:
                mod = c(bus=bus,
                         address=address,
                         module_info=module_type.message.module_info)
                mod.state_callback.add(gen_update_state_cb(address))
                return mod
            except ValueError:
                pass

        raise ValueError()

    except ValueError:
        return UnknownModule(bus=bus,
                             address=address,
                             module_info=module_type.message.module_info,
                             update_state_cb=gen_update_state_cb(address))
