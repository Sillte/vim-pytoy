from functools import cached_property

from pytoy.shared.lib.event import EventEmitter
from pytoy.shared.lib.event.global_event import GlobalEvent


class GlobalWindowEventProviderDummy:
    def __init__(self) -> None:
        self._winclosed_emitter = EventEmitter[int]()

    @cached_property
    def winclosed(self) -> GlobalEvent[int]:
        return GlobalEvent(self._winclosed_emitter.event)
