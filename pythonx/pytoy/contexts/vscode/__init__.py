from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from functools import cached_property
from pytoy.infra.core.entity import EntityRegistry
from pytoy.contexts.vim import GlobalVimContext


# Only for lazy loading to speed up. 
if TYPE_CHECKING:
    from pytoy.ui.pytoy_buffer.impls.vscode.kernel import VSCodeBufferKernel
    from pytoy.ui.pytoy_window.impls.vscode.kernel import VSCodeWindowKernel
    from pytoy.infra.autocmd.autocmd_manager import AutoCmdManager 


class GlobalVSCodeContext:
    _instance: ClassVar["GlobalVSCodeContext | None"] = None

    @classmethod
    def get(cls) -> GlobalVSCodeContext:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @cached_property
    def buffer_kernel_registry(self) -> EntityRegistry[int, VSCodeBufferKernel]:
        from pytoy.ui.pytoy_buffer.impls.vscode.kernel import VSCodeBufferKernel
        def factory(bufnr: int) -> VSCodeBufferKernel:
            return VSCodeBufferKernel(bufnr, ctx=self)
        return EntityRegistry(VSCodeBufferKernel, factory=factory)

    @cached_property
    def window_kernel_registry(self) -> EntityRegistry[int, VSCodeWindowKernel]:
        from pytoy.ui.pytoy_window.impls.vscode.kernel import VSCodeWindowKernel
        def factory(winid: int) -> VSCodeWindowKernel:
            return VSCodeWindowKernel(winid, ctx=self)
        return EntityRegistry(VSCodeWindowKernel, factory=factory)

    @cached_property
    def autocmd_manager(self) -> AutoCmdManager:
        from pytoy.infra.autocmd.autocmd_manager import AutoCmdManager 
        return AutoCmdManager()

    @property
    def vim_context(self) -> GlobalVimContext:
        return GlobalVimContext.get()
