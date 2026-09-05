from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Self, cast

from pytoy.shared.lib.backend import can_use_vim
from pytoy.shared.lib.event.global_event import GlobalEvent
from pytoy.shared.lib.events.domain import GlobalBufferEventProviderImpl
from pytoy.shared.lib.events.impls.dummy.buffer_events import GlobalBufferEventProviderDummy
from pytoy.shared.lib.events.impls.vim.buffer_events import GlobalBufferEventProviderVim

if TYPE_CHECKING:
    from pytoy.contexts.pytoy import GlobalPytoyContext
    from pytoy.contexts.vim import GlobalVimContext


from pytoy.shared.lib.event.domain import Event


def get_impl(ctx: GlobalPytoyContext | None = None) -> GlobalBufferEventProviderImpl:
    from pytoy.contexts.pytoy import GlobalPytoyContext

    ctx = ctx or GlobalPytoyContext.get()
    if can_use_vim():
        impl = GlobalBufferEventProviderVim(ctx.vim_context)
    else:
        impl = GlobalBufferEventProviderDummy()

    return cast(GlobalBufferEventProviderImpl, impl)


class GlobalBufferEventProvider:
    def __init__(self, impl: GlobalBufferEventProviderImpl | None = None) -> None:
        self._impl = impl or get_impl()

    @property
    def wipeout(self) -> GlobalEvent[int]:
        return self._impl.wipeout

    @cached_property
    def write_pre(self) -> GlobalEvent[int]:
        return self._impl.write_pre


class ScopedBufferEventProvider:
    def __init__(self, global_provider: GlobalBufferEventProvider | None = None) -> None:
        global_provider = global_provider or GlobalBufferEventProvider()
        self.global_provider = global_provider

    def get_wipeout_event(self, bufnr: int) -> Event[int]:
        wipeout_event = self.global_provider.wipeout
        return wipeout_event.at(bufnr)

    def get_write_pre(self, bufnr: int) -> Event[int]:
        return self.global_provider.write_pre.at(bufnr)

    @classmethod
    def from_ctx(cls, ctx: GlobalPytoyContext | GlobalVimContext) -> Self:
        # [TODO] This function should be considered to eliminate.
        from pytoy.contexts.vim import GlobalVimContext

        if isinstance(ctx, GlobalVimContext):
            impl = cast(GlobalBufferEventProviderImpl, GlobalBufferEventProviderVim(ctx=ctx))
        else:
            impl = get_impl(ctx)
        global_provider = GlobalBufferEventProvider(impl=impl)
        return cls(global_provider)
