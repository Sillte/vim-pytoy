from typing import Callable, Hashable, Protocol

from pytoy.shared.lib.event.domain import Disposable, Event


class MortalEntityProtocol[T](Protocol):
    @property
    def on_end(self) -> Event[T]:
        """Event when this entity is destroyed."""
        ...

    @property
    def entity_id(self) -> T: ...


class EntityRegistry[ID: Hashable, E: MortalEntityProtocol]:
    """Keep registered entities alive until their ``on_end`` event fires."""

    def __init__(
        self,
        entity_cls: type[E],
        *,
        factory: Callable[[ID], E] | None = None,
    ):
        self._entity_cls = entity_cls
        self._factory = factory or self._default_factory
        self._entities: dict[ID, E] = {}
        self._disposables: dict[ID, Disposable] = {}

    def _default_factory(self, entity_id: ID) -> E:
        return self._entity_cls(entity_id)  # type: ignore

    def get(self, entity_id: ID) -> E:
        if entity_id not in self._entities:
            entity = self._factory(entity_id)
            self._entities[entity_id] = entity
            self._disposables[entity_id] = entity.on_end.subscribe(lambda id_: self._dispose(id_))
        return self._entities[entity_id]

    def _dispose(self, entity_id: ID) -> None:
        self._entities.pop(entity_id, None)
        if disposable := self._disposables.pop(entity_id, None):
            disposable.dispose()
