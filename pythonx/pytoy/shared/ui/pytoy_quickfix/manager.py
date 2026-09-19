from pytoy.shared.lib.event import Event
from pytoy.shared.ui.pytoy_quickfix.entity import QuickfixEntity


class _NO_ENTITY_NAME: ...


class QuickfixEntityManager:
    def __init__(self) -> None:
        self._entities: dict[str | None, QuickfixEntity] = {}
        self._current_name: str | None | _NO_ENTITY_NAME = _NO_ENTITY_NAME()

    def create(self, name: str | None = "$default", *, owner_end: Event | None = None) -> QuickfixEntity:
        if name in self._entities:
            raise ValueError(f"Quickfix already exists: {name!r}")
        entity = QuickfixEntity(name=name, owner_end=owner_end)
        return self.register(entity, name=name)

    def register(self, entity: QuickfixEntity, *, name: str | None = None) -> QuickfixEntity:
        name = name or entity.name

        if name in self._entities:
            raise ValueError(f"Quickfix already exists: {name!r}")

        self._register(entity, name)
        return entity

    def update(self, name: str | None, *, owner_end: Event | None = None) -> QuickfixEntity:
        old_entity = self._entities.get(name)
        if old_entity is None:
            return self.create(name, owner_end=owner_end)

        self._entities.pop(name)
        old_entity.dispose()
        return self._register(QuickfixEntity(name=name, owner_end=owner_end), name)

    def _register(self, entity: QuickfixEntity, name: str | None) -> QuickfixEntity:
        def _dispose(_name: str | None) -> None:
            if self._entities.get(name) is not entity:
                return
            self._entities.pop(name, None)
            if self._current_name == name:
                self._current_name = next(iter(self._entities), _NO_ENTITY_NAME())

        entity.on_end.subscribe(_dispose)
        self._entities[name] = entity

        if isinstance(self._current_name, _NO_ENTITY_NAME):
            self._current_name = name

        return entity

    def get(self, name: str | None = "$default") -> QuickfixEntity | None:
        return self._entities.get(name)

    @property
    def current(self) -> QuickfixEntity | None:
        if isinstance(self._current_name, _NO_ENTITY_NAME):
            return None
        return self._entities[self._current_name]

    def set_current(self, name: str) -> QuickfixEntity:
        entity = self._entities.get(name)
        if entity is None:
            raise KeyError(name)
        self._current_name = name
        return self._entities[name]

    def remove(self, name: str | None) -> QuickfixEntity | None:
        entity = self._entities.pop(name, None)
        if entity is None:
            return None
        if self._current_name == name:
            self._current_name = next(iter(self._entities), _NO_ENTITY_NAME())
        entity.dispose()
        return entity
