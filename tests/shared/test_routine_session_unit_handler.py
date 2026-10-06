import threading

from pytoy.shared.lib.outcome import Success
from pytoy.shared.timertask.routine_session import (
    RoutineSessionHandler,
    RoutineSessionRequest,
    RoutineUnitIterationExit,
    RoutineUnitRequest,
)
from pytoy.shared.timertask.thread_execution import ThreadExecutionHandler


def test_unit_emits_execution_start_and_exit_events() -> None:
    session = RoutineSessionHandler.create(RoutineSessionRequest())
    unit = session.create_unit(RoutineUnitRequest(name="event-test", worker=lambda _: 42, max_iteration=1))
    started_executions = []
    iteration_exits: list[RoutineUnitIterationExit[int]] = []
    exit_received = threading.Event()

    unit.on_execution_start.subscribe(started_executions.append)

    def on_execution_exit(exit: RoutineUnitIterationExit[int]) -> None:
        iteration_exits.append(exit)
        exit_received.set()

    unit.on_iteration_exit.subscribe(on_execution_exit)

    try:
        unit.start()

        assert exit_received.wait(timeout=5)
        assert len(started_executions) == 1
        assert isinstance(started_executions[0], ThreadExecutionHandler)
        assert len(iteration_exits) == 1
        assert iteration_exits[0].name == "event-test"
        assert isinstance(iteration_exits[0].outcome, Success)
        assert iteration_exits[0].outcome.value == 42
    finally:
        session.terminate()
