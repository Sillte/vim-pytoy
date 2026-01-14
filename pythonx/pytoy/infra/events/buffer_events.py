from __future__ import annotations
from pytoy.infra.autocmd.autocmd_manager import get_autocmd_manager, AutoCmdManager, EmitSpec, PayloadMapper
from pytoy.infra.autocmd.vim_autocmd import EmitterPayload

from pytoy.infra.events.entity_event import GlobalEvent
from pytoy.infra.core.models.event import EventEmitter

from typing import Callable, Any, TYPE_CHECKING, Self
from functools import cached_property
from dataclasses import dataclass
if TYPE_CHECKING:
    from pytoy.contexts.vim import GlobalVimContext


from pytoy.infra.core.models.event import Event

# NOTE:
# Since the transform of PayloadMapper uses the functions for identity check. 
# So, the instance function is not appropriate`. 
def _to_bufnr(args) -> int:
    return int(args[0]) 

class GlobalBufferEventProvider:
    """
    NOTE: Since the `transform` of PayaloadMapper is regardes as the value  
    for checking the equivalentness, so `DO NOT lambda function here` 
    
    NOTE: SSOT of the events are `AutoCmdManager`. 
    Hence, `cached_property` is intended for only speeds.  
    """
    def __init__(self,  ctx: GlobalVimContext | None=None) -> None:
        if ctx is None:
            from pytoy.contexts.vim import GlobalVimContext
            ctx = GlobalVimContext.get()
        self._manager: AutoCmdManager = ctx.autocmd_manager

    @property
    def manager(self):
        return self._manager

    @cached_property
    def wipeout(self) -> GlobalEvent[int]:
        group: str = "PytoyAnyBufferClosedGroupAutocmd"
        emit_spec: EmitSpec =  EmitSpec(event="BufWipeout", pattern="*")
        payload_mapper: PayloadMapper =  PayloadMapper(arguments=["abuf"], transform=_to_bufnr)
        autocmd = self.manager.register(group, emit_spec, payload_mapper)
        return GlobalEvent(autocmd.event)

    @cached_property
    def write_pre(self) -> GlobalEvent[int]:
        group = "PytoyAnyBufferBufWritePreAutocmd"
        emit_spec = EmitSpec(event="BufWritePre", pattern="*")
        payload_mapper = PayloadMapper(arguments=["abuf"], transform=_to_bufnr)
        autocmd = self.manager.register(group, emit_spec, payload_mapper)
        return GlobalEvent(autocmd.event)


class ScopedBufferEventProvider:
    def __init__(self, global_provider: GlobalBufferEventProvider) -> None:
        self.global_provider = global_provider

    def get_wipeout_event(self, bufnr: int) -> Event[int]:
        wipeout_event = self.global_provider.wipeout
        return wipeout_event.at(bufnr)

    def get_write_pre(self, bufnr: int) -> Event[int]:
        return self.global_provider.write_pre.at(bufnr)

    @classmethod
    def from_ctx(cls, ctx: GlobalVimContext) -> Self:
        return cls(GlobalBufferEventProvider(ctx=ctx))


