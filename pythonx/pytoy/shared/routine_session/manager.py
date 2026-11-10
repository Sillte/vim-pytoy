from threading import RLock
from typing import Sequence

from .models import RoutineSession, RoutineSessionID, RoutineSessionQuery


class RoutineSessionManager:
    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: dict[RoutineSessionID, RoutineSession] = {}

    def register(self, session: RoutineSession) -> RoutineSession:
        with self._lock:
            self._sessions[session.id] = session

        def _deregister(_):
            with self._lock:
                self._sessions.pop(session.id, None)

        session.on_exit.subscribe(_deregister)
        return session

    def get_session(self, session_id: RoutineSessionID) -> RoutineSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def select(self, query: RoutineSessionQuery | None = None) -> Sequence[RoutineSession]:
        query = query if query is not None else RoutineSessionQuery.from_any()

        with self._lock:
            sessions = list(self._sessions.values())
        if query.id is not None:
            sessions = [elem for elem in sessions if elem.id == query.id]
        if query.kind is not None:
            sessions = [elem for elem in sessions if elem.kind == query.kind]
        return sessions
