from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from functools import cached_property
from pytoy.infra.core.entity import EntityRegistry
from pytoy.contexts.vim import GlobalVimContext
from pytoy.contexts.vscode import GlobalVSCodeContext
from pytoy.contexts.core import GlobalCoreContext


# Only for lazy loading to speed up. 
if TYPE_CHECKING:
    ...
    from pytoy.lib_tools.command_executor import CommandExecutionManager 
    #from pytoy.ui.pytoy_window.impls.vscode.kernel import VSCodeWindowKernel
    #from pytoy.infra.autocmd.autocmd_manager import AutoCmdManager 


class GlobalPytoyContext:
    _instance: ClassVar["GlobalPytoyContext | None"] = None

    @classmethod
    def get(cls) -> GlobalPytoyContext:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @cached_property
    def command_execution_manager(self) -> CommandExecutionManager:
        from pytoy.lib_tools.command_executor import CommandExecutionManager 
        return CommandExecutionManager()

    @property
    def vim_context(self) -> GlobalVimContext:
        return GlobalVimContext.get()

    @property
    def vscode_context(self) -> GlobalVSCodeContext:
        return GlobalVSCodeContext.get()

    @property
    def core_context(self) -> GlobalCoreContext:
        return GlobalCoreContext.get()
