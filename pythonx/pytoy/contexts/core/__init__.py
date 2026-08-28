from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from functools import cached_property


# Only for lazy loading to speed up.
if TYPE_CHECKING:
    from pytoy.job_execution.environment_manager import EnvironmentManager
    from pytoy.bootstrap.import_resolvers import LLMImportResolver
    from pytoy.shared.timertask.thread_execution.manager import ThreadExecutionManager

    ...
    # from pytoy.job_execution.command_executor import CommandExecutionManager
    # from pytoy.shared.ui.pytoy_window.impls.vscode.kernel import VSCodeWindowKernel
    # from pytoy.shared.lib.autocmd.autocmd_manager import AutoCmdManager


class GlobalCoreContext:
    _instance: ClassVar["GlobalCoreContext | None"] = None

    @classmethod
    def get(cls) -> GlobalCoreContext:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @cached_property
    def environment_manager(self) -> EnvironmentManager:
        from pytoy.job_execution.environment_manager import EnvironmentManager

        return EnvironmentManager()

    @cached_property
    def thread_execution_manager(self) -> ThreadExecutionManager:
        from pytoy.shared.timertask.thread_execution.manager import ThreadExecutionManager

        return ThreadExecutionManager()

    @cached_property
    def llm_import_resolver(sefl) -> LLMImportResolver:
        from pytoy.bootstrap.import_resolvers import LLMImportResolver

        moratorium_time = 1.0
        return LLMImportResolver(moratorium_time)
