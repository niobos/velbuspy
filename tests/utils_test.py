import sanic.request

from velbus.utils import cache_control_max_age


def test_max_age_no_header(generate_sanic_request):
    req = generate_sanic_request()
    assert None is cache_control_max_age(req)


def test_max_age_no_maxage(generate_sanic_request):
    h = {
        'Cache-Control': 'no-cache',
    }
    req = generate_sanic_request(headers=h)
    assert None is cache_control_max_age(req)


def test_max_age_maxage(generate_sanic_request):
    h = {
        'Cache-Control': 'no-cache, max-age=7',
    }
    req = generate_sanic_request(headers=h)
    assert 7 == cache_control_max_age(req)


def test_max_age_case_variant(generate_sanic_request):
    h = {
        'cacHE-conTRol': 'max-age=6',
    }
    req = generate_sanic_request(headers=h)
    assert 6 == cache_control_max_age(req)
