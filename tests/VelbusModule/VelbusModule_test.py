import asyncio
import contextvars
import dataclasses
import datetime
from unittest import mock

import typing

import freezegun
import pytest
from velbus.VelbusModule.VelbusModule import VelbusModule, DelayedCall


def test_datetime_delta():
    now = datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    # 00:00 UTC, 01:00 CET

    unaware_1h = DelayedCall(datetime.datetime(2000, 1, 1, 1, 0, 0))
    assert 3600 == unaware_1h.seconds_from_now(now)

    aware_1h_utc = DelayedCall(datetime.datetime(2000, 1, 1, 1, 0, 0, tzinfo=datetime.timezone.utc))
    assert 3600 == aware_1h_utc.seconds_from_now(now)

    aware_1h_cet = DelayedCall(datetime.datetime(2000, 1, 1, 2, 0, 0,
                                                 tzinfo=datetime.timezone(datetime.timedelta(hours=1))))
    assert 3600 == aware_1h_cet.seconds_from_now(now)

    now_vs_now = DelayedCall(datetime.datetime.now(tz=datetime.timezone.utc)).seconds_from_now()
    assert now_vs_now > -1
    assert now_vs_now < 1

    now_vs_utcnow = DelayedCall(datetime.datetime.utcnow()).seconds_from_now()
    assert now_vs_utcnow > -1
    assert now_vs_utcnow < 1


@freezegun.freeze_time("2000-01-01 00:00:00")
def test_delayedcall():
    d = DelayedCall()
    assert d.when is None

    d = DelayedCall(when=0)
    assert d.when == datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

    d = DelayedCall(when="2000-01-02 03:04:05 +02:00")
    assert d.when == datetime.datetime(2000, 1, 2, 1, 4, 5, tzinfo=datetime.timezone.utc)

    with pytest.raises(TypeError):
        DelayedCall(when={})

    with pytest.raises(TypeError):
        DelayedCall(foo="bar")


def test_delayed_calls():
    func = mock.Mock()
    cv = contextvars.ContextVar('cv')
    cv.set('initial')

    @dataclasses.dataclass()
    class CCallInfo(DelayedCall):
        param: str = ""

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


def test_delayed_calls_relative():
    func = mock.Mock()
    cv = contextvars.ContextVar('cv')
    cv.set('initial')

    @dataclasses.dataclass()
    class CCallInfo(DelayedCall):
        param: str = ""

    class C(VelbusModule):
        def delayed_call(self, call_info) -> typing.Any:
            func(call_info.param, cv.get())
            if call_info.param == "stop":
                asyncio.get_event_loop().stop()

    m = C(None, 1)
    m.delayed_calls = [
        CCallInfo(when=0.3, param="stop"),
        CCallInfo(when=0.2, param="two"),
        CCallInfo(when=0.1, param="one"),
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
