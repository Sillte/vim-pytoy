import gc
import weakref

from pytoy.shared.lib.entity import EntityRegistry
from pytoy.shared.lib.event import Event, EventEmitter


class _TestEntity:
    def __init__(self, entity_id: int) -> None:
        self._entity_id = entity_id
        self._end_emitter = EventEmitter[int]()

    @property
    def entity_id(self) -> int:
        return self._entity_id

    @property
    def on_end(self) -> Event[int]:
        return self._end_emitter.event


def test_registry_retains_entity_until_end_event() -> None:
    registry: EntityRegistry[int, _TestEntity] = EntityRegistry(_TestEntity)
    entity = registry.get(1)
    entity_ref = weakref.ref(entity)
    end_emitter = entity._end_emitter

    del entity
    gc.collect()

    retained_entity = registry.get(1)
    assert entity_ref() is retained_entity
    del retained_entity

    end_emitter.fire(1)
    gc.collect()

    assert entity_ref() is None
    assert registry.get(1).entity_id == 1
