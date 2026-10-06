from pytoy.shared.timertask.routine_session import (
    RoutineSessionHandler,
    RoutineSessionQuery,
    RoutineSessionRequest,
    RoutineUnitRequest,
)
from pytoy.shared.timertask.routine_session.manager import RoutineSessionManager


def test_create_query_and_terminate_session() -> None:
    manager = RoutineSessionManager()
    handler = RoutineSessionHandler.create(RoutineSessionRequest.from_any(kind="test"), manager=manager)
    exits = []
    handler.on_exit.subscribe(exits.append)

    assert handler.id
    assert handler.kind == "test"
    assert [item.id for item in RoutineSessionHandler.query(RoutineSessionQuery(kind="test"), manager=manager)] == [
        handler.id
    ]

    handler.terminate()

    assert [exit.id for exit in exits] == [handler.id]
    assert manager.get_session(handler.id) is None
    handler.terminate()


def test_session_handler_delegates_unit_access_and_termination() -> None:
    manager = RoutineSessionManager()
    session_handler = RoutineSessionHandler.create(RoutineSessionRequest(), manager=manager)

    unit_handler = session_handler.create_unit(RoutineUnitRequest(name="unit", worker=lambda _: None))

    assert unit_handler is not None
    assert unit_handler.alive is False
    unit_handler.start()
    assert unit_handler.alive is True

    assert session_handler.get_unit("unit") is not None

    session_handler.terminate()

    assert manager.get_session(session_handler.id) is None

    assert unit_handler.alive is False


def test_create_uses_global_manager_by_default() -> None:
    handler = RoutineSessionHandler.create(RoutineSessionRequest.from_any(kind="global-default"))

    assert [item.id for item in RoutineSessionHandler.query(RoutineSessionQuery(kind="global-default"))] == [handler.id]

    handler.terminate()
