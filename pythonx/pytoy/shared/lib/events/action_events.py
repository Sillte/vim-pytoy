from pytoy.shared.lib.keymap import KeymapManager, KeySequence, KeymapSpec
from pytoy.shared.lib.event.domain import Event


class KeyActionEvents:
    def __init__(self, manager: KeymapManager, bufnr: int | None) -> None:
        self._manager = manager
        self._bufnr = bufnr
        self._events: dict[KeySequence, Event] = {}

    def __getitem__(self, key: KeySequence) -> Event:
        spec = KeymapSpec(key=key, buffer=self._bufnr)
        event = self._events.get(spec.key)
        if event is not None:
            return event
        keymap = self._manager.register(spec)
        self._events[keymap.key] = keymap.event
        return keymap.event

    def __delitem__(self, key: KeySequence):
        spec = KeymapSpec(key=key, buffer=self._bufnr)
        self._manager.deregister(spec)
        self._events.pop(key, None)

    def clear(self) -> None:
        keys = list(self._events)
        for key in keys:
            del self._events[key]
