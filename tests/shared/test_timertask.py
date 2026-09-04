import threading

import pytest

from pytoy.shared.timertask import TimerStopException, TimerTask
from pytoy.shared.timertask.impls.dummy import TimerTaskImplDummy


@pytest.fixture
def dummy_impl():
    impl = TimerTaskImplDummy()
    previous_impl = TimerTask.impl
    TimerTask.set_impl(impl)
    try:
        yield impl
    finally:
        TimerTask.impl = previous_impl


def test_execute_oneshot_runs_and_deregisters(dummy_impl):
    completed = threading.Event()
    calls = []

    name = TimerTask.execute_oneshot(lambda: (calls.append("called"), completed.set()), interval=1, name="oneshot")

    assert name == "oneshot"
    assert completed.wait(1)
    assert calls == ["called"]
    assert not TimerTask.is_registered(name)


def test_repeat_runs_requested_number_of_times_and_finishes(dummy_impl):
    completed = threading.Event()
    calls = []

    def on_finish(reason):
        assert reason == "finished"
        completed.set()

    TimerTask.register(lambda: calls.append("called"), interval=1, repeat=3, on_finish=on_finish)

    assert completed.wait(1)
    assert calls == ["called", "called", "called"]


def test_callback_error_invokes_on_error_and_deregisters(dummy_impl):
    failed = threading.Event()
    errors = []

    def task():
        raise ValueError("failed")

    def on_error(error):
        errors.append(error)
        failed.set()

    name = TimerTask.register(task, interval=1, name="failing", on_error=on_error)

    assert failed.wait(1)
    assert isinstance(errors[0], ValueError)
    assert not TimerTask.is_registered(name)


def test_deregister_strict_rejects_unknown_name(dummy_impl):
    with pytest.raises(KeyError):
        TimerTask.deregister("missing", strict=True)


def test_timer_stop_exception_finishes_as_stopped(dummy_impl):
    completed = threading.Event()
    reasons = []

    def task():
        raise TimerStopException()

    def on_finish(reason):
        reasons.append(reason)
        completed.set()

    TimerTask.register(task, interval=1, on_finish=on_finish)

    assert completed.wait(1)
    assert reasons == ["stopped"]
