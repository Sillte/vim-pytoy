from typing import Protocol, Hashable
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
    def __init__(self, entity_cls: type[E]):
        self._entity_cls = entity_cls
        self._entities:  WeakValueDictionary[ID, E] = WeakValueDictionary({})

    @property
    def entity_cls(self) -> type[E]:
        return self._entity_cls

    def get(self, entity_id: ID) -> E:
        if entity_id not in self._entities:
            entity = self._entity_cls(entity_id)  # type: ignore
            self._entities[entity_id] = entity
            entity.on_end.subscribe(lambda id_: self._dispose(id_))
        return self._entities[entity_id]

    def _dispose(self, entity_id: ID) -> None:
        self._entities.pop(entity_id, None)


class EntityRegistryProvider[ID: Hashable, T: MortalEntityProtocol]:
    _registries: dict[type[T], EntityRegistry[ID, T]] = dict()

    @classmethod
    def get(cls, entity_cls: type[T]) -> EntityRegistry[ID, T]:
        if entity_cls in cls._registries:
            return cls._registries[entity_cls]
        cls._registries[entity_cls] = EntityRegistry(entity_cls)
        return cls._registries[entity_cls]



