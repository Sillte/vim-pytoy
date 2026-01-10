from typing import Protocol, Hashable, Callable
from weakref import WeakValueDictionary

from pytoy.infra.core.models.event import Event


class MortalEntityProtocol[T](Protocol):

    @property
    def on_end(self) -> Event[T]:
        """Event when this entity is destroyed.
        """
        ...
    @property
    def entity_id(self) -> T:
        ...


class EntityRegistry[ID: Hashable, E: MortalEntityProtocol]:
    def __init__(
        self,
        entity_cls: type[E],
        *,
        factory: Callable[[ID], E] | None = None,
    ):
        self._entity_cls = entity_cls
        self._factory = factory or self._default_factory
        self._entities: WeakValueDictionary[ID, E] = WeakValueDictionary()

    def _default_factory(self, entity_id: ID) -> E:
        return self._entity_cls(entity_id)  # type: ignore

    def get(self, entity_id: ID) -> E:
        if entity_id not in self._entities:
            entity = self._factory(entity_id)
            self._entities[entity_id] = entity
            entity.on_end.subscribe(lambda id_: self._dispose(id_))
        return self._entities[entity_id]

    def _dispose(self, entity_id: ID) -> None:
        self._entities.pop(entity_id, None)
