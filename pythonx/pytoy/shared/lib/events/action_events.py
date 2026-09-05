from typing import Sequence

from pytoy.shared.lib.backend import can_use_vim
from pytoy.shared.lib.event import Event
from pytoy.shared.lib.events.domain.action import KeyEventManagerImpl, KeymapSpec, KeySequence
from pytoy.shared.lib.events.impls.dummy.action_events import DummyKeyEventManager
from pytoy.shared.lib.events.impls.vim.action_events import VimKeyEventManager


def get_impl() -> KeyEventManagerImpl:
    if can_use_vim():
        return VimKeyEventManager()
    return DummyKeyEventManager()


class KeyEventManager:
    def __init__(self, impl: KeyEventManagerImpl | None = None):
        impl = impl or get_impl()
        self._impl = impl

    def register(self, spec: KeymapSpec) -> Event[int | None]:
        return self._impl.register(spec)

    def deregister(self, spec: KeymapSpec):
        self._impl.deregister(spec)

    @property
    def specs(self) -> Sequence[KeymapSpec]:
        return self._impl.specs


class KeyActionEvents:
    """
    If BufferID is None, then the key action is applied to all the buffers.
    """

    def __init__(self, buffer: int | None, *, manager: KeyEventManager | None = None) -> None:
        from pytoy.contexts.core import GlobalCoreContext

        self._manager = manager or GlobalCoreContext.get().key_event_manager
        self._buffer = buffer

    def __getitem__(self, key: KeySequence | str) -> Event[int | None]:
        normalized_key = KeySequence(key)
        spec = KeymapSpec(key=normalized_key, buffer=self._buffer)
        return self._manager.register(spec)

    def __delitem__(self, key: KeySequence):
        spec = KeymapSpec(key=key, buffer=self._buffer)
        self._manager.deregister(spec)

    def clear(self) -> None:
        for spec in tuple(self._manager.specs):
            if spec.buffer == self._buffer:
                self._manager.deregister(spec)
