from typing import Sequence

from pytoy.shared.lib.event import Event, EventEmitter
from pytoy.shared.lib.events.domain.action import KeymapSpec


class DummyKeyEventManager:
    def __init__(self) -> None:
        self._emitters: dict[KeymapSpec, EventEmitter] = {}

    def register(self, spec: KeymapSpec) -> Event[int | None]:
        if spec in self._emitters:
            return self._emitters[spec].event

        self._emitters[spec] = EventEmitter[int]()
        return self._emitters[spec].event

    def deregister(self, spec: KeymapSpec):
        self._emitters.pop(spec, None)

    @property
    def specs(self) -> Sequence[KeymapSpec]:
        return tuple(self._emitters)
