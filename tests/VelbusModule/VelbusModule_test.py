import asyncio
import contextvars
import dataclasses
import datetime
from unittest import mock

import typing

from velbus.VelbusModule.VelbusModule import VelbusModule, DelayedCall


def test_datetime_delta():
    now = datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    # 00:00 UTC, 01:00 CET

    unaware_1h = datetime.datetime(2000, 1, 1, 1, 0, 0)
    assert 3600 == VelbusModule.datetime_to_relative_seconds(unaware_1h, now)

    aware_1h_utc = datetime.datetime(2000, 1, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
    assert 3600 == VelbusModule.datetime_to_relative_seconds(aware_1h_utc, now)

    aware_1h_cet = datetime.datetime(2000, 1, 1, 2, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=1),))
    assert 3600 == VelbusModule.datetime_to_relative_seconds(aware_1h_cet, now)

    now_vs_now = VelbusModule.datetime_to_relative_seconds(datetime.datetime.now(tz=datetime.timezone.utc))
    assert now_vs_now > -1
    assert now_vs_now < 1

    now_vs_utcnow = VelbusModule.datetime_to_relative_seconds(datetime.datetime.utcnow())
    assert now_vs_utcnow > -1
    assert now_vs_utcnow < 1


def test_delayed_calls():
    func = mock.Mock()
    cv = contextvars.ContextVar('cv')
    cv.set('initial')

    @dataclasses.dataclass()
    class CCallInfo(DelayedCall):
        param: str

    class C(VelbusModule):
        def delayed_call(self, call_info) -> typing.Any:
            func(call_info.param, cv.get())
            if call_info.param == "stop":
                asyncio.get_event_loop().stop()

    m = C(None, 1)
    now = datetime.datetime.utcnow()
    m.delayed_calls = [
        CCallInfo(when=now + datetime.timedelta(milliseconds=300), param="stop"),
        CCallInfo(when=now + datetime.timedelta(milliseconds=200), param="two"),
        CCallInfo(when=now + datetime.timedelta(milliseconds=100), param="one"),
    ]

    cv.set('changed')
    # should not propagate, since context was copied during
    # the delayed_calls assignment

    asyncio.get_event_loop().run_forever()

    func.assert_has_calls([
        mock.call("one", "initial"),
        mock.call("two", "initial"),
        mock.call("stop", "initial"),
    ])