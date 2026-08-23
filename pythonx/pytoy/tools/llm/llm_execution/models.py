from __future__ import annotations
from typing import Any, Self

import uuid
import logging

from typing import Any, Callable, Sequence
from pytoy_llm.task.models import TaskSpec, TaskContextState, TaskResponse

import time
from dataclasses import dataclass, field
from pytoy.shared.lib.event.domain import Event

from pytoy.shared.timertask.thread_executor import ThreadExecution

type ExecutionID = str
type ExecutionKind = str


@dataclass(frozen=True)
class LLMExecution:
    thread_execution: ThreadExecution
    on_exit: Event[Any]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=lambda: time.time())


@dataclass(frozen=True)
class ExecutionRequest[T]:
    task_spec: TaskSpec
    input: Any
    context_state: TaskContextState | None = None
    kind: ExecutionKind = "$default"
    logger: logging.Logger | None = None

    @classmethod
    def from_any(
        cls,
        task_spec: TaskSpec,
        input: Any,
        context_state: TaskContextState | None = None,
        kind: ExecutionKind = "$default",
        logger: logging.Logger | None = None,
    ) -> Self:
        return cls(task_spec=task_spec, input=input, context_state=context_state, kind=kind, logger=logger)


@dataclass(frozen=True)
class ExecutionContext:
    request: ExecutionRequest
    hooks: ExecutionHooks

    @property
    def kind(self) -> ExecutionKind:
        return self.request.kind


@dataclass(frozen=True)
class ExecutionResult[T]:
    execution_id: str
    task_response: TaskResponse[T]

    def output(self) -> T:
        return self.task_response.output


@dataclass(frozen=True)
class ExecutionHooks:
    """Recommendation policy... Use `on_finish` rather than on_success / on_failure."""

    on_success: Callable[[Any], None] | None = None
    on_failure: Callable[[Exception], None] | None = None

    @staticmethod
    def merge(hook1: "ExecutionHooks", hook2: "ExecutionHooks") -> "ExecutionHooks":
        from dataclasses import fields

        merged_kwargs = {}
        for item in fields(ExecutionHooks):
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
        return ExecutionHooks(**merged_kwargs)


@dataclass(frozen=True)
class ExecutionQuery:
    kind: ExecutionKind | None = None
    ...


@dataclass(frozen=True)
class ExecutionPolicy:
    kind: ExecutionKind | None = None
    allow_parallel: bool = False
