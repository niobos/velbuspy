import sanic.request

from utils import cache_control_max_age


def test_max_age_no_header():
    req = sanic.request.Request(b'/', {}, 1.1, 'GET', None)
    assert None is cache_control_max_age(req)


def test_max_age_no_maxage():
    h = {
        'Cache-Control': 'no-cache',
    }
    req = sanic.request.Request(b'/', h, 1.1, 'GET', None)
    assert None is cache_control_max_age(req)


def test_max_age_maxage():
    h = {
        'Cache-Control': 'no-cache, max-age=7',
    }
    req = sanic.request.Request(b'/', h, 1.1, 'GET', None)
    assert 7 == cache_control_max_age(req)


def test_max_age_case_variant():
    h = {
        'cacHE-conTRol': 'max-age=6',
    }
    req = sanic.request.Request(b'/', h, 1.1, 'GET', None)
    assert 6 == cache_control_max_age(req)
