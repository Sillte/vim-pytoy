from typing import Protocol

from pytoy.shared.lib.event import Event


class WindowEvents(Protocol):
    """Semantic events emitted for windows."""

    @property
    def winclosed(self) -> Event[int]: ...
