from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, ClassVar

# Only for lazy loading to speed up.
if TYPE_CHECKING:
    from pytoy.bootstrap.import_resolvers import LLMImportResolver
    from pytoy.shared.timertask.manager import TimerTaskManager
    from pytoy.shared.timertask.thread_execution.manager import ThreadExecutionManager
    from pytoy.tool_execution.execution_environment import EnvironmentManager

    ...


class GlobalCoreContext:
    _instance: ClassVar["GlobalCoreContext | None"] = None

    @classmethod
    def get(cls) -> GlobalCoreContext:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @cached_property
    def environment_manager(self) -> EnvironmentManager:
        from pytoy.tool_execution.execution_environment.manager import EnvironmentManager

        return EnvironmentManager()

    @cached_property
    def thread_execution_manager(self) -> ThreadExecutionManager:
        from pytoy.shared.timertask.thread_execution.manager import ThreadExecutionManager

        return ThreadExecutionManager()

    @cached_property
    def timer_task_manager(self) -> TimerTaskManager:
        from pytoy.shared.timertask.manager import TimerTaskManager

        return TimerTaskManager()

    @cached_property
    def llm_import_resolver(sefl) -> LLMImportResolver:
        from pytoy.bootstrap.import_resolvers import LLMImportResolver

        moratorium_time = 1.0
        return LLMImportResolver(moratorium_time)
