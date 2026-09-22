import logging
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, Self

from pytoy_llm.task.models import TaskContextState, TaskRequest
from pytoy_llm.task.session import TaskSessionHandler, TaskSessionRequest

from pytoy.shared.lib.event import Event, EventEmitter
from pytoy.shared.ui.pytoy_buffer import BufferMetadata, BufferSource, PytoyBuffer, make_buffer
from pytoy.tool_execution.llm import LLMExecutionHandler

from .logger import get_llm_logger

type LLMSessionKind = str
# If the LLM retains the conversation, it is a `session`.
type LLMSessionID = str
type LLMSessionMetadata = Mapping[str, Any]


@dataclass(frozen=True)
class LLMSessionBufferHooks:
    on_creation: Callable[[PytoyBuffer], None] | None = None
    on_wiped: Callable[[PytoyBuffer], None] | None = None
    actions: dict[str, Callable[[PytoyBuffer], None]] | None = None

    def apply(self, buffer: PytoyBuffer) -> None:
        if self.on_creation:
            self.on_creation(buffer)

        if self.on_wiped:
            on_wiped = self.on_wiped
            buffer.on_wiped.subscribe(lambda _: on_wiped(buffer))

        if self.actions is not None:
            for key, func in self.actions.items():
                buffer.actions[key].subscribe(lambda _: func(buffer))


class LLMSessionBufferProvider:
    def __init__(self, buffer_source: BufferSource, hooks: LLMSessionBufferHooks):
        self._buffer_source = buffer_source
        self._hooks = hooks

    def provide(self) -> PytoyBuffer:
        return self.buffer

    @property
    def buffer(self) -> PytoyBuffer:
        buffer = make_buffer(source=self._buffer_source, metadata=BufferMetadata(kind="llm-session"))
        self._hooks.apply(buffer)
        return buffer

    @property
    def buffer_source(self) -> BufferSource:
        return self._buffer_source


class LLMSessionDriverProtocol(Protocol):
    def make_progress(
        self,
        execution_creator: Callable[[TaskRequest], LLMExecutionHandler],
        llm_buffer_provider: LLMSessionBufferProvider,
        user_prompt: str,
    ) -> None: ...


@dataclass(frozen=True)
class LLMSessionRequest:
    driver: LLMSessionDriverProtocol
    buffer_source: BufferSource
    buffer_hooks: LLMSessionBufferHooks
    task_context: TaskContextState
    kind: LLMSessionKind = "$default"
    metadata: LLMSessionMetadata = field(default_factory=dict)
    logger: logging.Logger | None = None

    @classmethod
    def from_any(
        cls,
        driver: LLMSessionDriverProtocol,
        buffer_source: BufferSource | None = None,
        buffer_hooks: LLMSessionBufferHooks | None = None,
        task_context: TaskContextState | None = None,
        kind: LLMSessionKind | None = None,
        metadata: LLMSessionMetadata | None = None,
        logger: logging.Logger | None = None,
    ) -> Self:
        kind = kind or "$default"
        buffer_source = buffer_source or BufferSource.from_no_file("__idea_space_llm__")
        buffer_hooks = buffer_hooks or LLMSessionBufferHooks()
        task_context = task_context or TaskContextState()
        return cls(
            driver=driver,
            buffer_source=buffer_source,
            buffer_hooks=buffer_hooks,
            task_context=task_context,
            kind=kind,
            metadata=dict(metadata or {}),
            logger=logger,
        )


@dataclass(frozen=True)
class LLMSessionExit:
    buffer: PytoyBuffer
    task_context: TaskContextState


@dataclass(frozen=True)
class LLMSessionQuery:
    buffer_source: BufferSource | None = None
    kind: LLMSessionKind | None = None
    metadata: LLMSessionMetadata | None = None

    @classmethod
    def from_any(
        cls,
        buffer_source: BufferSource | PytoyBuffer | None = None,
        kind: LLMSessionKind | None = None,
        metadata: LLMSessionMetadata | None = None,
    ) -> Self:
        if isinstance(buffer_source, PytoyBuffer):
            buffer_source = buffer_source.source
        return cls(buffer_source=buffer_source, kind=kind, metadata=dict(metadata) if metadata is not None else None)


class LLMSession:
    def __init__(
        self,
        driver: LLMSessionDriverProtocol,
        buffer_source: BufferSource,
        buffer_hooks: LLMSessionBufferHooks,
        task_context: TaskContextState,
        kind: LLMSessionKind,
        metadata: LLMSessionMetadata,
        logger: logging.Logger | None,
    ):
        self._driver = driver
        self._buffer_source = buffer_source
        self._buffer_hooks = buffer_hooks
        self._task_context = task_context
        self._buffer: PytoyBuffer | None = None
        self._id = str(uuid.uuid4())
        self._kind = kind
        self._metadata = dict(metadata)
        self._logger = logger or get_llm_logger()

        self._terminated = False
        self._exit_emitter = EventEmitter[LLMSessionExit]()
        self._llm_buffer_provider = LLMSessionBufferProvider(self._buffer_source, hooks=self._buffer_hooks)

        task_session_request = TaskSessionRequest.from_any(kind=self._kind, context_state=self._task_context)
        self._task_session_handler = TaskSessionHandler.create(task_session_request)

    @classmethod
    def from_request(cls, request: LLMSessionRequest) -> Self:
        return cls(
            driver=request.driver,
            buffer_source=request.buffer_source,
            buffer_hooks=request.buffer_hooks,
            task_context=request.task_context,
            kind=request.kind,
            metadata=request.metadata,
            logger=request.logger,
        )

    @property
    def buffer(self) -> PytoyBuffer:
        return self._llm_buffer_provider.provide()

    @property
    def buffer_source(self) -> BufferSource:
        return self._llm_buffer_provider.buffer_source

    @property
    def buffer_provider(self) -> LLMSessionBufferProvider:
        return self._llm_buffer_provider

    @property
    def id(self) -> LLMSessionID:
        return self._id

    @property
    def kind(self) -> LLMSessionKind:
        return self._kind

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def metadata(self) -> LLMSessionMetadata:
        return dict(self._metadata)

    @property
    def driver(self) -> LLMSessionDriverProtocol:
        return self._driver

    @property
    def task_session_handler(self) -> TaskSessionHandler:
        return self._task_session_handler

    @property
    def on_exit(self) -> Event[LLMSessionExit]:
        return self._exit_emitter.event

    def terminate(self) -> None:
        if self._terminated:
            return
        self._terminated = True
        self._task_session_handler.terminate()
        self._exit_emitter.dispose()
