from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from pytoy.shared.lib.autocmd.autocmd_manager import AutoCmdManager, EmitSpec, PayloadMapper
from pytoy.shared.lib.event.global_event import GlobalEvent

if TYPE_CHECKING:
    from pytoy.contexts.vim import GlobalVimContext


def _to_bufnr(args) -> int:
    return int(args[0])


class GlobalBufferEventProviderVim:
    def __init__(self, ctx: GlobalVimContext | None = None) -> None:
        if ctx is None:
            from pytoy.contexts.vim import GlobalVimContext

            ctx = GlobalVimContext.get()
        self._manager: AutoCmdManager = ctx.autocmd_manager

    @property
    def manager(self) -> AutoCmdManager:
        return self._manager

    @cached_property
    def wipeout(self) -> GlobalEvent[int]:
        group = "PytoyAnyBufferClosedGroupAutocmd"
        emit_spec = EmitSpec(event="BufWipeout", pattern="*")
        payload_mapper = PayloadMapper(arguments=["abuf"], transform=_to_bufnr)
        autocmd = self.manager.register(group, emit_spec, payload_mapper)
        return GlobalEvent(autocmd.event)

    @cached_property
    def write_pre(self) -> GlobalEvent[int]:
        group = "PytoyAnyBufferBufWritePreAutocmd"
        emit_spec = EmitSpec(event="BufWritePre", pattern="*")
        payload_mapper = PayloadMapper(arguments=["abuf"], transform=_to_bufnr)
        autocmd = self.manager.register(group, emit_spec, payload_mapper)
        return GlobalEvent(autocmd.event)
