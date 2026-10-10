import threading
import time

import pytest

from pytoy.shared.lib.outcome import Success
from pytoy.shared.timertask.routine_session import (
    RoutineSessionHandler,
    RoutineSessionRequest,
    RoutineUnitHooks,
    RoutineUnitIterationExit,
    RoutineUnitRequest,
)


def wait_for_unit_removal(session: RoutineSessionHandler, name: str) -> None:
    deadline = time.monotonic() + 5
    while session.get_unit(name) is not None and time.monotonic() < deadline:
        time.sleep(0.01)
    assert session.get_unit(name) is None


def test_preparing_listener_error_leaves_unit_unstarted_and_allows_retry() -> None:
    session = RoutineSessionHandler.create(RoutineSessionRequest())
    unit = session.create_unit(RoutineUnitRequest(name="prepare-test", worker=lambda _: 42, max_iteration=1))
    exit_received = threading.Event()

    def fail_preparation(_) -> None:
        raise RuntimeError("preparation failed")

    disposable = unit.on_execution_preparing.subscribe(fail_preparation)
    unit.on_iteration_exit.subscribe(lambda _: exit_received.set())

    try:
        with pytest.raises(RuntimeError, match="preparation failed"):
            unit.start()

        assert not unit.alive
        disposable.dispose()
        unit.start()
        assert exit_received.wait(timeout=5)
    finally:
        session.terminate()


def test_iteration_callback_errors_do_not_prevent_unit_termination() -> None:
    session = RoutineSessionHandler.create(RoutineSessionRequest())
    hook_calls = 0
    event_received = threading.Event()

    def fail_hook(_) -> None:
        nonlocal hook_calls
        hook_calls += 1
        raise RuntimeError("hook failed")

    unit = session.create_unit(
        RoutineUnitRequest(name="iteration-error", worker=lambda _: None, max_iteration=1),
        hooks=RoutineUnitHooks.from_any(on_exit=fail_hook),
    )

    def fail_event(_) -> None:
        event_received.set()
        raise ValueError("event failed")

    unit.on_iteration_exit.subscribe(fail_event)

    try:
        unit.start()
        assert event_received.wait(timeout=5)
        wait_for_unit_removal(session, "iteration-error")
        assert hook_calls == 1
        assert not unit.alive
    finally:
        session.terminate()


def test_unit_emits_execution_preparing_and_exit_events() -> None:
    session = RoutineSessionHandler.create(RoutineSessionRequest())
    unit = session.create_unit(RoutineUnitRequest(name="event-test", worker=lambda _: 42, max_iteration=1))
    preparing_states: list[bool] = []
    iteration_exits: list[RoutineUnitIterationExit[int]] = []
    exit_received = threading.Event()

    unit.on_execution_preparing.subscribe(lambda _: preparing_states.append(unit.alive))

    def on_execution_exit(exit: RoutineUnitIterationExit[int]) -> None:
        iteration_exits.append(exit)
        exit_received.set()

    unit.on_iteration_exit.subscribe(on_execution_exit)

    try:
        unit.start()

        assert exit_received.wait(timeout=5)
        assert preparing_states == [False]
        assert len(iteration_exits) == 1
        assert iteration_exits[0].name == "event-test"
        assert isinstance(iteration_exits[0].outcome, Success)
        assert iteration_exits[0].outcome.value == 42
    finally:
        session.terminate()
