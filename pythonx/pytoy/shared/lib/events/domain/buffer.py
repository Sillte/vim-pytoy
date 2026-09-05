from typing import Protocol

from pytoy.shared.lib.event import Event
from pytoy.shared.lib.event.global_event import GlobalEvent


class BufferEvents(Protocol):
    """Semantic events emitted for buffers."""

    @property
    def wipeout(self) -> Event[int]: ...

    @property
    def write_pre(self) -> Event[int]: ...


class GlobalBufferEventProviderImpl(Protocol):
    @property
    def wipeout(self) -> GlobalEvent[int]: ...

    @property
    def write_pre(self) -> GlobalEvent[int]: ...
