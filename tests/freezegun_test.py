import asyncio
import pytest
import freezegun


@pytest.fixture(params=[1, 2])
def number(request):
    """Returns a number"""
    return request.param


async def do_stuff(num):
    await asyncio.sleep(0.001)
    return num


@pytest.mark.asyncio
async def test_do_stuff(number):
    with freezegun.freeze_time() as frozen_datetime:
        coro = do_stuff(number)
        result = await coro
        assert result == number
