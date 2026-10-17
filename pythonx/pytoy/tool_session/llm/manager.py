from threading import RLock
from typing import Sequence

from .models import LLMSession, LLMSessionID, LLMSessionQuery


class LLMSessionManager:
    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: dict[LLMSessionID, LLMSession] = dict()

    def register(self, session: LLMSession) -> None:
        with self._lock:
            self._sessions[session.id] = session

        def _deregister(_):
            with self._lock:
                self._sessions.pop(session.id, None)

        session.on_exit.subscribe(_deregister)

    def select(self, query: LLMSessionQuery | None = None) -> Sequence[LLMSession]:
        query = query or LLMSessionQuery()
        with self._lock:
            sessions = list(self._sessions.values())
            if query.kind is not None:
                sessions = [session for session in sessions if session.kind == query.kind]
            if query.buffer_source is not None:
                sessions = [session for session in sessions if session.buffer_source == query.buffer_source]
            if query.metadata is not None:
                sessions = [
                    session
                    for session in sessions
                    if all(session.metadata.get(key) == value for key, value in query.metadata.items())
                ]
            return sessions

    def get(self, id_: LLMSessionID) -> LLMSession | None:
        with self._lock:
            return self._sessions.get(id_)

    def remove(self, id_: LLMSessionID) -> LLMSession | None:
        with self._lock:
            return self._sessions.pop(id_, None)
