from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.shared.timertask import backend_or_main_thread_only
from pytoy.tool_execution.llm.manager import LLMExecutionManager
from pytoy.tool_execution.llm.models import (
    LLMExecutionHooks,
    LLMExecutionKind,
    LLMExecutionQuery,
    LLMExecutionRequest,
)

from .handler import LLMExecutionHandler


class LLMExecutor[T]:
    def __init__(self, *, ctx: GlobalPytoyContext | None = None):
        if ctx is None:
            ctx = GlobalPytoyContext.get()
        self._execution_manager = ctx.llm_execution_manager

    @property
    def execution_manager(self) -> LLMExecutionManager:
        return self._execution_manager

    @backend_or_main_thread_only
    def execute(
        self, request: LLMExecutionRequest[T], hooks: LLMExecutionHooks[T] | None = None
    ) -> LLMExecutionHandler:
        handler = LLMExecutionHandler.create(request, manager=self.execution_manager)
        handler.start(hooks=hooks)
        return handler

    def can_execute(self, kind: LLMExecutionKind | None = None) -> bool:
        query = LLMExecutionQuery(kind=kind)
        handlers = LLMExecutionHandler.query(query=query, manager=self.execution_manager)
        if handlers:
            return False
        return True
