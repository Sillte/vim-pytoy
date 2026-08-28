import logging
from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.shared.lib.event.domain import EventEmitter

from typing import Any

from pytoy.shared.timertask.thread_execution import ThreadExecutionRequest, ThreadExecutor, ThreadExecutionHooks
from pytoy_llm.event_sinks import LoggerEventSink
from pytoy_llm.task import TaskRequest, TaskExecutor
from pytoy.tools.llm.llm_execution.models import (
    LLMExecutionRequest,
    LLMExecutionHooks,
    ExecutionPolicy,
    LLMExecutionKind,
    LLMExecutionQuery,
)
from pytoy.tools.llm.llm_execution.manager import LLMExecutionManager
from .handler import LLMExecutionHandler


class LLMExecutor[T]:
    def __init__(self, *, ctx: GlobalPytoyContext | None = None):
        if ctx is None:
            ctx = GlobalPytoyContext.get()
        self._execution_manager = ctx.llm_execution_manager

    @property
    def execution_manager(self) -> LLMExecutionManager:
        return self._execution_manager

    def execute(
        self, request: LLMExecutionRequest[T], hooks: LLMExecutionHooks[T] | None = None
    ) -> LLMExecutionHandler:
        handler = LLMExecutionHandler.create(request)
        handler.start(hooks=hooks)
        return handler

    def can_execute(self, kind: LLMExecutionKind | None = None) -> bool:
        query = LLMExecutionQuery(kind=kind)
        handlers = LLMExecutionHandler.query(query=query)
        if handlers:
            return False
        return True
