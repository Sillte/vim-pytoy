from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from functools import cached_property


# Only for lazy loading to speed up. 
if TYPE_CHECKING:
    from pytoy.job_execution.environment_manager import EnvironmentManager
    from pytoy.shared.timertask.thread_executor import ThreadExecutionManager
    ...
    #from pytoy.job_execution.command_executor import CommandExecutionManager 
    #from pytoy.shared.ui.pytoy_window.impls.vscode.kernel import VSCodeWindowKernel
    #from pytoy.shared.lib.autocmd.autocmd_manager import AutoCmdManager 


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
        from pytoy.shared.timertask.thread_executor import ThreadExecutionManager
        return ThreadExecutionManager()
