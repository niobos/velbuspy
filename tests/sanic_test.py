import asyncio
import contextvars
import threading
import time
import urllib.request
from unittest import mock

from sanic import Sanic
import sanic.request
import sanic.response

from .utils import make_async


def test_simple_get():
    app = Sanic(__name__)
    app.config.LOGO = None
    get_slash = mock.Mock(return_value=sanic.response.text("ok"))
    app.add_route(make_async(get_slash), '/', methods=['GET'])

    request, response = app.test_client.get('/')

    assert response.status == 200
    get_slash.assert_called_once()


def test_context_vars():
    """
    Test if ContextVar works as expected in sanic request handlers
    """
    cv = contextvars.ContextVar('cv')

    async def handle_get(request: sanic.request, path: str) -> sanic.response:
        print(f"Start get {path}")
        cv.set(path)
        await asyncio.sleep(0.5)
        print(f"End get {path}, cv={cv.get()}")
        return sanic.response.text(f"{path} {cv.get()}")

    async def quit(request: sanic.request) -> sanic.response:
        print("Received /stop")
        app.stop()
        return sanic.response.text("ok")

    app = Sanic(__name__)
    app.config.LOGO = None
    app.add_route(quit, '/stop', methods=['GET'])
    app.add_route(handle_get, '/test/<path:.*>', methods=['GET'])

    def do_get(ret, wait=0, path="/", timeout=10):
        time.sleep(wait)
        req = urllib.request.urlopen("http://127.0.0.1:22334" + path, timeout=timeout)
        body = req.read()
        ret['status'] = req.status
        ret['body'] = body

    get_a_ret = {}
    get_a_thread = threading.Thread(target=do_get, args=(get_a_ret, 0.1, "/test/a"))
    get_a_thread.start()
    get_b_ret = {}
    get_b_thread = threading.Thread(target=do_get, args=(get_b_ret, 0.1, "/test/b"))
    get_b_thread.start()

    stop_thread = threading.Thread(target=do_get, args=({}, 1, "/stop", 0.1))
    stop_thread.start()
    app.run(host="127.0.0.1", port=22334)

    get_a_thread.join()
    get_b_thread.join()
    stop_thread.join()

    asyncio.set_event_loop(asyncio.new_event_loop())  # leave with an non-stopped loop

    assert get_a_ret == {'status': 200, 'body': b'a a'}
    assert get_b_ret == {'status': 200, 'body': b'b b'}
