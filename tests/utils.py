import asyncio

import typing


def make_awaitable(ret) -> asyncio.Future:
    f = asyncio.get_event_loop().create_future()
    f.set_result(ret)
    return f


def make_async(func: typing.Callable):
    async def afunc(*args, **kwargs):
        ret = func(*args, **kwargs)
        await asyncio.sleep(0)
        return ret

    return afunc
