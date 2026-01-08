from pytoy.infra.autocmd.autocmd_manager import get_autocmd_manager, AutoCmdManager, EmitSpec, PayloadMapper
from pytoy.infra.autocmd.vim_autocmd import EmitterPayload

from pytoy.infra.events.entity_event import GlobalEvent
from pytoy.infra.core.models.event import EventEmitter

from typing import Callable, Any
from functools import cached_property
from dataclasses import dataclass


from pytoy.infra.core.models.event import Event


class GlobalBufferEventProvider:
    def __init__(self, manager: AutoCmdManager) -> None:
        self._manager = manager

    @property
    def manager(self):
        return self._manager

    @cached_property
    def wipeout(self) -> GlobalEvent[int]:
        group: str = "PytoyAnyBufferClosedGroupAutocmd"
        emit_spec: EmitSpec =  EmitSpec(event="BufWipeout")
        payload_mapper: PayloadMapper =  PayloadMapper(arguments=["abuf"], transform=lambda args: int(args[0]))
        autocmd = self.manager.register(group, emit_spec, payload_mapper)
        return GlobalEvent(autocmd.event)


global_provider = GlobalBufferEventProvider(get_autocmd_manager())

class ScopedBufferEventProvider:
    global_provider:  GlobalBufferEventProvider = global_provider

    @classmethod
    def get_wipeout_event(cls, bufnr: int) -> Event[int]:
        wipeout_event = cls.global_provider.wipeout
        return wipeout_event.at(bufnr)


