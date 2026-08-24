import logging  
from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.shared.lib.event.domain import EventEmitter

from typing import Any

from pytoy.shared.timertask.thread_execution import ThreadExecutionRequest, ThreadExecutor, ThreadExecutionHooks
from pytoy_llm.event_sinks import LoggerEventSink
from pytoy_llm.task import TaskRequest, TaskExecutor
from pytoy.tools.llm.llm_execution.models import ExecutionRequest, ExecutionHooks, LLMExecution, ExecutionPolicy, ExecutionKind, ExecutionContext
from pytoy.tools.llm.llm_execution.manager import LLMExecutionManager


class LLMExecutor:
    def __init__(self, *, ctx: GlobalPytoyContext | None = None): 
        if ctx is None:
            ctx = GlobalPytoyContext.get()
        self._execution_manager = ctx.llm_execution_manager

    @property
    def execution_manager(self) -> LLMExecutionManager:
        return self._execution_manager

    def execute(
        self, request: ExecutionRequest, hooks: ExecutionHooks | None = None
    ) -> LLMExecution:
        if hooks is None:
            hooks = ExecutionHooks()

        task_request = TaskRequest(spec=request.task_spec, input=request.input, context_state=request.context_state)

        execution_end_emitter = EventEmitter[Any]()

        def _on_finish(sync_output: Any):
            try:
                if hooks.on_success:
                    hooks.on_success(sync_output)
            except Exception as e:
                print("Unhandled exception at `on_success`", e)
            execution_end_emitter.fire(None)

        def _on_error(exception: Exception):
            try:
                if hooks.on_failure:
                    hooks.on_failure(exception)
            except Exception as e:
                print("Unhandled exception at `on_failure`", e)
            execution_end_emitter.fire(None)

        def _main(_) -> Any:
            logger = request.logger
            if logger:
                event_sink = LoggerEventSink(request.logger)
            else:
                event_sink = None
            
            task_response = TaskExecutor().execute(request=task_request, event_sink=event_sink)
            return task_response.output

        execution_request = ThreadExecutionRequest(main_func=_main)
        execution_hooks = ThreadExecutionHooks.from_any(on_finish=_on_finish, on_error=_on_error)
        thread_handler = ThreadExecutor().execute_with_creation(execution_request, hooks=execution_hooks)
        llm_execution = LLMExecution(thread_handler=thread_handler, on_exit=execution_end_emitter.event)
        llm_context = ExecutionContext(hooks=hooks, request=request)
        self.execution_manager.register(llm_execution,  llm_context)
        return llm_execution

    def can_execute(self, _: ExecutionRequest, kind: ExecutionKind | None = None) -> bool:
        policy = ExecutionPolicy(kind=kind)
        return self._execution_manager.can_execute(policy)
