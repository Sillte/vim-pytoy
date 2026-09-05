from typing import Protocol

from pytoy.shared.lib.event.global_event import GlobalEvent


class GlobalWindowEventProviderImpl(Protocol):
    @property
    def winclosed(self) -> GlobalEvent[int]: ...
