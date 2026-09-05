from functools import cached_property

from pytoy.shared.lib.event import EventEmitter
from pytoy.shared.lib.event.global_event import GlobalEvent


class GlobalBufferEventProviderDummy:
    def __init__(self) -> None:
        self._wipeout_emitter = EventEmitter[int]()
        self._write_pre_emitter = EventEmitter[int]()

    @cached_property
    def wipeout(self) -> GlobalEvent[int]:
        return GlobalEvent(self._wipeout_emitter.event)

    @cached_property
    def write_pre(self) -> GlobalEvent[int]:
        return GlobalEvent(self._write_pre_emitter.event)
