from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, ClassVar

from pytoy.contexts.core import GlobalCoreContext
from pytoy.contexts.vim import GlobalVimContext
from pytoy.contexts.vscode import GlobalVSCodeContext

# Only for lazy loading to speed up.
if TYPE_CHECKING:
    ...
    from pytoy.tool_execution.command.manager import CommandExecutionManager
    from pytoy.tool_execution.llm.manager import LLMExecutionManager
    from pytoy.tool_execution.terminal.infra.driver import TerminalDriverManager
    from pytoy.tool_execution.terminal.manager import TerminalExecutionManager
    # from pytoy.shared.ui.pytoy_window.impls.vscode.kernel import VSCodeWindowKernel
    # from pytoy.shared.autocmd.autocmd_manager import AutoCmdManager


class GlobalPytoyContext:
    _instance: ClassVar["GlobalPytoyContext | None"] = None

    @classmethod
    def get(cls) -> GlobalPytoyContext:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @cached_property
    def command_execution_manager(self) -> CommandExecutionManager:
        from pytoy.tool_execution.command.manager import CommandExecutionManager

        return CommandExecutionManager()

    @cached_property
    def terminal_execution_manager(self) -> TerminalExecutionManager:
        from pytoy.tool_execution.terminal.manager import TerminalExecutionManager

        return TerminalExecutionManager()

    @cached_property
    def terminal_driver_manager(self) -> TerminalDriverManager:
        from pytoy.tool_execution.terminal.infra.driver import TerminalDriverManager

        return TerminalDriverManager()

    @cached_property
    def llm_execution_manager(self) -> LLMExecutionManager:
        from pytoy.tool_execution.llm.manager import LLMExecutionManager

        return LLMExecutionManager()

    @property
    def vim_context(self) -> GlobalVimContext:
        return GlobalVimContext.get()

    @property
    def vscode_context(self) -> GlobalVSCodeContext:
        return GlobalVSCodeContext.get()

    @property
    def core_context(self) -> GlobalCoreContext:
        return GlobalCoreContext.get()
