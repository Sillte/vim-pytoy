import threading

import pytest

from pytoy.contexts.core import GlobalCoreContext
from pytoy.shared.timertask import TimerStopException, TimerTask
from pytoy.shared.timertask.impls.dummy import TimerTaskImplDummy
from pytoy.shared.timertask.manager import TimerTaskManager


@pytest.fixture
def dummy_impl():
    impl = TimerTaskImplDummy()
    context = GlobalCoreContext.get()
    previous_manager = context.__dict__.get("timer_task_manager")
    context.timer_task_manager = TimerTaskManager(impl)
    try:
        yield impl
    finally:
        if previous_manager is None:
            context.__dict__.pop("timer_task_manager", None)
        else:
            context.timer_task_manager = previous_manager


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


def test_zero_repeat_runs_once_and_finishes(dummy_impl):
    completed = threading.Event()
    calls = []

    def on_finish(reason):
        assert reason == "finished"
        completed.set()

    TimerTask.register(lambda: calls.append("called"), interval=1, repeat=0, on_finish=on_finish)

    assert completed.wait(1)
    assert calls == ["called"]


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


def test_register_rejects_duplicate_name(dummy_impl):
    TimerTask.register(lambda: None, interval=1000, name="duplicate")

    with pytest.raises(ValueError, match="already registered"):
        TimerTask.register(lambda: None, interval=1000, name="duplicate")


def test_manager_maps_public_name_to_unique_impl_name(dummy_impl):
    TimerTask.register(lambda: None, interval=1000, name="same")
    TimerTask.register(lambda: None, interval=1000, name="other")

    assert set(dummy_impl.tasks) != {"same", "other"}
    assert TimerTask.is_registered("same")
    assert TimerTask.is_registered("other")


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


def test_finish_callback_error_does_not_invoke_error_callback(dummy_impl):
    finished = threading.Event()
    errors = []

    def on_finish(_reason):
        finished.set()
        raise RuntimeError("finish callback failed")

    def on_error(error):
        errors.append(error)

    TimerTask.register(lambda: None, interval=1, repeat=1, on_finish=on_finish, on_error=on_error)

    assert finished.wait(1)
    assert errors == []
