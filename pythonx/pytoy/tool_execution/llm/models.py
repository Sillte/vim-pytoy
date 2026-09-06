from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Self

from pytoy_llm.task.execution import TaskExecutionHandler
from pytoy_llm.task.execution.models import TaskExecutionID, TaskExecutionStatus
from pytoy_llm.task.models import TaskContextState, TaskResult, TaskSpec

from pytoy.shared.lib.event import Event, EventEmitter
from pytoy.shared.lib.outcome import Outcome

type LLMExecutionID = TaskExecutionID
type LLMExecutionKind = str
type LLMExecutionStatus = TaskExecutionStatus


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
class LLMExecution[T]:
    request: LLMExecutionRequest[T]
    task_handler: TaskExecutionHandler[T]
    exit_emitter: EventEmitter[LLMExecutionExit[T]]

    @property
    def kind(self) -> LLMExecutionKind:
        return self.request.kind

    @property
    def id(self) -> LLMExecutionID:
        return self.task_handler.id

    @property
    def on_exit(self) -> Event[LLMExecutionExit[T]]:
        return self.exit_emitter.event


@dataclass(frozen=True)
class LLMExecutionContext[T]:
    request: LLMExecutionRequest[T]
    hooks: LLMExecutionHooks[T]

    @property
    def kind(self) -> LLMExecutionKind:
        return self.request.kind


@dataclass(frozen=True)
class LLMExecutionResult[T]:
    task_result: TaskResult[T]

    @property
    def output(self) -> T:
        return self.task_result.output

    @property
    def context_state(self) -> TaskContextState:
        return self.task_result.context_state


@dataclass(frozen=True)
class LLMExecutionExit[T]:
    id: str
    outcome: Outcome[LLMExecutionResult[T], Exception]


@dataclass(frozen=True)
class LLMExecutionHooks[T]:
    """Recommendation policy... Use `on_finish` rather than on_success / on_failure."""

    on_result: Callable[[LLMExecutionResult[T]], None]
    on_exception: Callable[[Exception], None]

    @staticmethod
    def merge(hook1: LLMExecutionHooks[T], hook2: LLMExecutionHooks[T]) -> LLMExecutionHooks[T]:
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
    def from_any(
        cls,
        on_result: Callable[[LLMExecutionResult[T]], None] | None = None,
        on_exception: Callable[[Exception], None] | None = None,
        on_output: Callable[[T], None] | None = None,
    ) -> Self:
        def _resolve_handle_output(
            target: Callable[[LLMExecutionResult[T]], None],
            on_output: Callable[[T], None],
        ) -> Callable[[LLMExecutionResult[T]], None]:

            def handler(result: LLMExecutionResult[T]) -> None:
                target(result)
                on_output(result.output)

            return handler

        on_result = on_result or (lambda _: None)
        on_exception = on_exception or (lambda _: None)
        on_result = _resolve_handle_output(on_result, on_output) if on_output else on_result
        return cls(on_result=on_result, on_exception=on_exception)


@dataclass(frozen=True)
class LLMExecutionQuery:
    kind: LLMExecutionKind | None = None
    status: LLMExecutionStatus | None = None
