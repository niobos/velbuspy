import asyncio


def make_awaitable(ret) -> asyncio.Future:
    f = asyncio.get_event_loop().create_future()
    f.set_result(ret)
    return f
