from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from functools import cached_property
from pytoy.infra.core.entity import EntityRegistry


# Only for lazy loading to speed up. 
if TYPE_CHECKING:
    from pytoy.ui.pytoy_buffer.impls.vim.kernel import VimBufferKernel
    from pytoy.ui.pytoy_window.impls.vim.kernel import VimWindowKernel
    from pytoy.infra.autocmd.autocmd_manager import AutoCmdManager 


class GlobalVimContext:
    _instance: ClassVar["GlobalVimContext | None"] = None

    @classmethod
    def get(cls) -> GlobalVimContext:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @cached_property
    def buffer_kernel_registry(self) -> EntityRegistry[int, VimBufferKernel]:
        from pytoy.ui.pytoy_buffer.impls.vim.kernel import VimBufferKernel
        return EntityRegistry(VimBufferKernel)

    @cached_property
    def window_kernel_registry(self) -> EntityRegistry[int, VimWindowKernel]:
        from pytoy.ui.pytoy_window.impls.vim.kernel import VimWindowKernel
        return EntityRegistry(VimWindowKernel)

    @cached_property
    def autocmd_manager(self) -> AutoCmdManager:
        from pytoy.infra.autocmd.autocmd_manager import AutoCmdManager 
        return AutoCmdManager()
