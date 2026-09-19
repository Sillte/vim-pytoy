from pathlib import Path
from threading import RLock
from typing import Sequence

from pytoy.shared.lib.event import Event
from pytoy.shared.ui.pytoy_quickfix.entity import QuickfixEntity
from pytoy.shared.ui.pytoy_quickfix.models import QuickfixID, QuickfixQuery


class _NO_ENTITY: ...


class QuickfixEntityManager:
    def __init__(self) -> None:
        self._lock = RLock()
        self._entities: dict[QuickfixID, QuickfixEntity] = {}
        self._current_id: QuickfixID | _NO_ENTITY = _NO_ENTITY()

    def create(
        self, kind: str = "$default", *, owner_end: Event | None = None, working_directory: Path | None = None
    ) -> QuickfixEntity:
        entity = QuickfixEntity(kind=kind, owner_end=owner_end, working_directory=working_directory)
        return self.register(entity)

    def register(self, entity: QuickfixEntity) -> QuickfixEntity:
        with self._lock:
            if entity.id in self._entities:
                raise ValueError(f"Quickfix already exists: {entity.id!r}")

            def _dispose(_id: QuickfixID) -> None:
                with self._lock:
                    self._entities.pop(_id, None)
                    if self._current_id == _id:
                        self._current_id = next(iter(self._entities), _NO_ENTITY())

            self._entities[entity.id] = entity
            entity.on_end.subscribe(_dispose)

            if isinstance(self._current_id, _NO_ENTITY):
                self._current_id = entity.id

            return entity

    def get(self, id_: QuickfixID) -> QuickfixEntity | None:
        with self._lock:
            return self._entities.get(id_)

    def query(self, query: QuickfixQuery | None = None) -> Sequence[QuickfixEntity]:
        with self._lock:
            query = query or QuickfixQuery.from_any()
            entities = tuple(self._entities.values())
            if query.kind is not None:
                entities = tuple(elem for elem in entities if elem.kind == query.kind)
            return entities

    @property
    def current(self) -> QuickfixEntity | None:
        with self._lock:
            if isinstance(self._current_id, _NO_ENTITY):
                return None
            return self._entities[self._current_id]

    def set_current(self, id_: QuickfixID) -> QuickfixEntity:
        with self._lock:
            entity = self._entities.get(id_)
            if entity is None:
                raise KeyError(id_)
            self._current_id = id_
            return self._entities[id_]

    def remove(self, id_: QuickfixID) -> QuickfixEntity | None:
        with self._lock:
            entity = self._entities.pop(id_, None)
            if entity is None:
                return None
            if self._current_id == id_:
                self._current_id = next(iter(self._entities), _NO_ENTITY())
            entity.dispose()
            return entity
