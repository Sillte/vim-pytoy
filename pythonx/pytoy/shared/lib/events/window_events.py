from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Self, cast

from pytoy.shared.lib.backend import can_use_vim
from pytoy.shared.lib.event.domain import Event
from pytoy.shared.lib.event.global_event import GlobalEvent
from pytoy.shared.lib.events.domain import GlobalWindowEventProviderImpl
from pytoy.shared.lib.events.impls.dummy.window_events import GlobalWindowEventProviderDummy
from pytoy.shared.lib.events.impls.vim.window_events import GlobalWindowEventProviderVim

if TYPE_CHECKING:
    from pytoy.contexts.pytoy import GlobalPytoyContext
    from pytoy.contexts.vim import GlobalVimContext


def get_impl(ctx: GlobalVimContext | None = None) -> GlobalWindowEventProviderImpl:
    if can_use_vim():
        return cast(GlobalWindowEventProviderImpl, GlobalWindowEventProviderVim(ctx))
    return cast(GlobalWindowEventProviderImpl, GlobalWindowEventProviderDummy())


class GlobalWindowEventProvider:
    def __init__(self, impl: GlobalWindowEventProviderImpl | None = None) -> None:
        self._impl = impl or get_impl()

    @cached_property
    def winclosed(self) -> GlobalEvent[int]:
        return self._impl.winclosed

    @classmethod
    def from_ctx(cls, ctx: GlobalVimContext | GlobalPytoyContext) -> Self:
        # [TODO] This function should be considered to eliminate.
        from pytoy.contexts.vim import GlobalVimContext

        if isinstance(ctx, GlobalVimContext):
            impl = cast(GlobalWindowEventProviderImpl, GlobalWindowEventProviderVim(ctx))
        else:
            impl = cast(GlobalWindowEventProviderImpl, GlobalWindowEventProviderDummy())
        return cls(impl)


class ScopedWindowEventProvider:
    def __init__(self, global_provider: GlobalWindowEventProvider | None = None) -> None:
        self.global_provider = global_provider or GlobalWindowEventProvider()

    def get_winclosed_event(self, winid: int) -> Event[int]:
        winclosed = self.global_provider.winclosed
        return winclosed.at(winid)

    @classmethod
    def from_ctx(cls, ctx: GlobalVimContext) -> Self:
        # [TODO] This function should be considered to eliminate.
        global_provider = GlobalWindowEventProvider.from_ctx(ctx)
        return cls(global_provider)
