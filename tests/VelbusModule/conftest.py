"""
Shared fixtures for use in tests
"""


import pytest
import sanic.request

from velbus import HttpApi


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
