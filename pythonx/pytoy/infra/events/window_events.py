from __future__ import annotations
from pytoy.infra.autocmd.autocmd_manager import get_autocmd_manager, EmitSpec, PayloadMapper, AutoCmdManager

from pytoy.infra.core.models.event import Event
from pytoy.infra.events.entity_event import  GlobalEvent
from functools import cached_property
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from pytoy.contexts.vim import GlobalVimContext


def _to_winid(args) -> int:
    return int(args[0]) 

class GlobalWindowEventProvider:
    """
    NOTE: Since the `transform` of PayaloadMapper is regardes as the value  
    for checking the equivalentness, so `DO NOT lambda function here` 
    """
    def __init__(self,  ctx: GlobalVimContext | None=None) -> None:
        if ctx is None:
            from pytoy.contexts.vim import GlobalVimContext
            ctx = GlobalVimContext.get()
        self._manager: AutoCmdManager = ctx.autocmd_manager
        
    @cached_property
    def winclosed(self) -> GlobalEvent[int]:
        group = f"PytoyAnyWinClosedGroup_{id(self._manager)}"
        emit_spec = EmitSpec(event="WinClosed")
        payload_mapper = PayloadMapper(arguments=["afile"], transform=_to_winid)
        autocmd = self._manager.register(group, emit_spec, payload_mapper)
        return GlobalEvent(autocmd.event)


class ScopedWindowEventProvider:
    def __init__(self, global_provider: GlobalWindowEventProvider) -> None:
        self.global_provider = global_provider

    def get_winclosed_event(self, bufnr: int) -> Event[int]:
        winclosed = self.global_provider.winclosed
        return winclosed.at(bufnr)

    @classmethod
    def from_ctx(cls, ctx: GlobalVimContext) -> Self:
        return cls(GlobalWindowEventProvider(ctx=ctx))
