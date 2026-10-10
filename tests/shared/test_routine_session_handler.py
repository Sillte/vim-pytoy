import uuid

import pytest

from pytoy.shared.timertask.routine_session import (
    RoutineSessionHandler,
    RoutineSessionQuery,
    RoutineSessionRequest,
    RoutineUnitRequest,
)


def test_create_query_and_terminate_session() -> None:
    kind = f"test-{uuid.uuid4()}"
    handler = RoutineSessionHandler.create(RoutineSessionRequest.from_any(kind=kind))
    exits = []
    handler.on_exit.subscribe(exits.append)

    assert handler.id
    assert handler.kind == kind
    assert [item.id for item in RoutineSessionHandler.query(RoutineSessionQuery(kind=kind))] == [handler.id]

    handler.terminate()

    assert [exit.id for exit in exits] == [handler.id]
    assert RoutineSessionHandler.query(RoutineSessionQuery(id=handler.id)) == []
    handler.terminate()


def test_session_exit_listener_error_propagates_after_session_removal() -> None:
    kind = f"exit-error-{uuid.uuid4()}"
    handler = RoutineSessionHandler.create(RoutineSessionRequest(kind=kind))

    def fail_on_exit(_):
        raise RuntimeError("exit listener failed")

    handler.on_exit.subscribe(fail_on_exit)

    with pytest.raises(RuntimeError, match="exit listener failed"):
        handler.terminate()

    assert RoutineSessionHandler.query(RoutineSessionQuery(id=handler.id)) == []
    handler.terminate()


def test_session_handler_delegates_unit_access_and_termination() -> None:
    session_handler = RoutineSessionHandler.create(RoutineSessionRequest())

    unit_handler = session_handler.create_unit(RoutineUnitRequest(name="unit", worker=lambda _: None))

    assert unit_handler is not None
    assert unit_handler.alive is False
    unit_handler.start()
    assert unit_handler.alive is True

    assert session_handler.get_unit("unit") is not None

    session_handler.terminate()

    assert RoutineSessionHandler.query(RoutineSessionQuery(id=session_handler.id)) == []

    assert unit_handler.alive is False


def test_create_uses_global_manager_by_default() -> None:
    kind = f"global-default-{uuid.uuid4()}"
    handler = RoutineSessionHandler.create(RoutineSessionRequest.from_any(kind=kind))

    assert [item.id for item in RoutineSessionHandler.query(RoutineSessionQuery(kind=kind))] == [handler.id]

    handler.terminate()
