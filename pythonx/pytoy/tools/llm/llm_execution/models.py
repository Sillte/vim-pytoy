from __future__ import annotations
from typing import Any, Self

import uuid
import logging

from typing import Callable
from pytoy_llm.task.models import TaskSpec, TaskContextState, TaskResponse

import time
from dataclasses import dataclass, field
from pytoy.shared.lib.event import Event, EventEmitter
from pytoy.shared.lib.outcome import Outcome, Success, Failure

from pytoy.shared.timertask.thread_execution import ThreadExecutionHandler, ThreadExecutionRequest, ThreadExecutionStatus, ThreadExecutionExit

type LLMExecutionID = str
type LLMExecutionStatus = ThreadExecutionStatus
type LLMExecutionKind = str



@dataclass(frozen=True)
class LLMExecutionRequest[T]:
    task_spec: TaskSpec[T]
    input: Any
    context_state: TaskContextState | None = None
    kind: LLMExecutionKind = "$default"
    logger: logging.Logger | None = None

    @classmethod
    def from_any(
        cls,
        task_spec: TaskSpec,
        input: Any,
        context_state: TaskContextState | None = None,
        kind: LLMExecutionKind = "$default",
        logger: logging.Logger | None = None,
    ) -> Self:
        return cls(task_spec=task_spec, input=input, context_state=context_state, kind=kind, logger=logger)


@dataclass(frozen=True)
class LLMExecutionContext[T]:
    request: LLMExecutionRequest[T]
    hooks: LLMExecutionHooks

    @property
    def kind(self) -> LLMExecutionKind:
        return self.request.kind


@dataclass(frozen=True)
class LLMExecutionResult[T]:
    execution_id: str
    task_response: TaskResponse[T]

    def output(self) -> T:
        return self.task_response.output

@dataclass(frozen=True)
class LLMExecutionExit[T]:
    id: str
    outcome: Outcome[TaskResponse[T], Exception]


@dataclass(frozen=True)
class LLMExecutionHooks[T]:
    """Recommendation policy... Use `on_finish` rather than on_success / on_failure."""

    on_success: Callable[[T], None]
    on_failure: Callable[[Exception], None]

    @staticmethod
    def merge(hook1: "LLMExecutionHooks", hook2: "LLMExecutionHooks") -> "LLMExecutionHooks":
        from dataclasses import fields

        merged_kwargs = {}
        for item in fields(LLMExecutionHooks):
            f1 = getattr(hook1, item.name)
            f2 = getattr(hook2, item.name)

            if not f1:  # (f1= None, f2=None), (f1=None, f2=Callable)
                merged_kwargs[item.name] = f2
            elif not f2:  # (f1=Callable, f2=None)
                merged_kwargs[item.name] = f1
            else:

                def _merged(f1=f1, f2=f2):  # デフォルト引数でクロージャの参照を固定
                    return lambda *a, **k: (f1(*a, **k), f2(*a, **k))

                merged_kwargs[item.name] = _merged()
        return LLMExecutionHooks(**merged_kwargs)

    @classmethod
    def from_any(cls, on_success: Callable[[T], None] | None = None, on_failure: Callable[[Exception], None] | None = None) -> Self:
        on_success = on_success or (lambda _: None)
        on_failure = on_failure or (lambda _: None)
        return cls(on_success=on_success, on_failure=on_failure)
        


@dataclass(frozen=True)
class LLMExecutionQuery:
    kind: LLMExecutionKind | None = None
    status: LLMExecutionStatus | None = None


@dataclass(frozen=True)
class ExecutionPolicy:
    kind: LLMExecutionKind | None = None
    allow_parallel: bool = False


@dataclass
class LLMExecution[T]:
    thread_handler: ThreadExecutionHandler
    request: LLMExecutionRequest[T]
    status: LLMExecutionStatus = "created"
    on_exit_emitter: EventEmitter[LLMExecutionExit] = field(default_factory=lambda: EventEmitter())
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: time.time())

    @classmethod
    def from_any(cls, thread_handler: ThreadExecutionHandler | ThreadExecutionRequest, llm_request: LLMExecutionRequest[T]) -> Self:
        if isinstance(thread_handler, ThreadExecutionRequest): 
            thread_handler = ThreadExecutionHandler.create(thread_handler)

        return cls(thread_handler=thread_handler, request=llm_request)

    def start(self, hooks: LLMExecutionHooks) -> None:
        self.status = "running"
        self.hooks = hooks

        self.thread_handler.on_exit.subscribe(self._resolve_exit)
                        

    @property
    def on_exit(self) -> Event[LLMExecutionExit]:
        return self.on_exit_emitter.event


    def _resolve_exit(self, exit_entity: ThreadExecutionExit[LLMExecutionExit, Exception]) -> None:
        match exit_entity.outcome:
            case Success(value):
                llm_exit_entity = LLMExecutionExit(id=self.id, outcome=value.outcome)
            case Failure(error):
                llm_exit_entity = LLMExecutionExit(id=self.id, outcome=Failure(error))
        self.on_exit_emitter.fire(llm_exit_entity)


