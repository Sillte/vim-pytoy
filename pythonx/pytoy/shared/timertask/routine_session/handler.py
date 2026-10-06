from typing import Self, Sequence

from pytoy.contexts.core import GlobalCoreContext
from pytoy.shared.lib.event import Event
from pytoy.shared.timertask.routine_session.unit.handler import RoutineUnitHandler
from pytoy.shared.timertask.routine_session.unit.models import (
    RoutineUnitHooks,
    RoutineUnitName,
    RoutineUnitRequest,
)

from .manager import RoutineSessionManager
from .models import (
    RoutineSession,
    RoutineSessionExit,
    RoutineSessionID,
    RoutineSessionKind,
    RoutineSessionQuery,
    RoutineSessionRequest,
)


class RoutineSessionHandler:
    def __init__(self, id: RoutineSessionID, *, manager: RoutineSessionManager) -> None:
        self._id = id
        self._manager = manager

    @classmethod
    def create(cls, request: RoutineSessionRequest, *, manager: RoutineSessionManager | None = None) -> Self:
        if manager is None:
            manager = GlobalCoreContext.get().routine_session_manager
        session = RoutineSession.from_request(request)
        manager.register(session)
        return cls(id=session.id, manager=manager)

    @classmethod
    def query(
        cls, query: RoutineSessionQuery | None = None, *, manager: RoutineSessionManager | None = None
    ) -> Sequence[Self]:
        if manager is None:
            manager = GlobalCoreContext.get().routine_session_manager
        sessions = manager.select(query)
        return [cls(id=session.id, manager=manager) for session in sessions]

    def create_unit[T](
        self, request: RoutineUnitRequest[T], hooks: RoutineUnitHooks[T] | None = None
    ) -> RoutineUnitHandler:
        return self._require_session().create_unit(request, hooks)

    def get_unit(self, name: RoutineUnitName) -> RoutineUnitHandler | None:
        return self._require_session().get_unit(name)

    def terminate(self) -> None:
        session = self._manager.get_session(self._id)
        if session is not None:
            session.terminate()

    @property
    def id(self) -> RoutineSessionID:
        return self._id

    @property
    def kind(self) -> RoutineSessionKind:
        return self._require_session().kind

    @property
    def on_exit(self) -> Event[RoutineSessionExit]:
        return self._require_session().on_exit

    def _require_session(self) -> RoutineSession:
        session = self._manager.get_session(self._id)
        if session is None:
            raise ValueError(f"Session is already terminated. `{self._id=}`")
        return session
