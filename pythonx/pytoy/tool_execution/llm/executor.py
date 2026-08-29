import threading
from functools import wraps
from typing import Callable

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.tool_execution.llm.manager import LLMExecutionManager
from pytoy.tool_execution.llm.models import (
    LLMExecutionHooks,
    LLMExecutionKind,
    LLMExecutionQuery,
    LLMExecutionRequest,
)

from .handler import LLMExecutionHandler


def main_thread_only[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError("This method must be called from the main thread.")
        return func(*args, **kwargs)

    return wrapper


class LLMExecutor[T]:
    def __init__(self, *, ctx: GlobalPytoyContext | None = None):
        if ctx is None:
            ctx = GlobalPytoyContext.get()
        self._execution_manager = ctx.llm_execution_manager

    @property
    def execution_manager(self) -> LLMExecutionManager:
        return self._execution_manager

    @main_thread_only
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
