from typing import Protocol

from pytoy.shared.lib.event import Event


class BufferEvents(Protocol):
    """Semantic events emitted for buffers."""

    @property
    def wipeout(self) -> Event[int]: ...

    @property
    def write_pre(self) -> Event[int]: ...
