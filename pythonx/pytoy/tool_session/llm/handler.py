from concurrent.futures import Future
from dataclasses import replace
from threading import Lock, current_thread
from typing import Any, Callable, Self, Sequence

from pytoy_llm.activity_sinks import LoggerActivitySink
from pytoy_llm.task.models import TaskRequest

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.shared.lib.event import Event
from pytoy.shared.timertask import backend_thread_dispatch
from pytoy.tool_execution.llm import LLMExecutionExit, LLMExecutionHandler

from .manager import LLMSessionManager
from .models import (
    LLMSession,
    LLMSessionBufferProvider,
    LLMSessionDriverProtocol,
    LLMSessionExit,
    LLMSessionID,
    LLMSessionInterfaceMode,
    LLMSessionMetadata,
    LLMSessionQuery,
    LLMSessionRequest,
)


class _SingleExecutionCreator:
    def __init__(
        self,
        create_handler: Callable[[TaskRequest], LLMExecutionHandler],
        on_exit: Callable[[LLMExecutionExit[Any]], None],
    ) -> None:
        self._create_handler = create_handler
        self._on_exit = on_exit
        self._owner_thread = current_thread()
        self._called = False
        self._closed = False
        self._lock = Lock()

    def __call__(self, task_request: TaskRequest) -> LLMExecutionHandler:
        if current_thread() is not self._owner_thread:
            raise RuntimeError("The execution creator must be called synchronously by the session driver.")
        with self._lock:
            if self._called or self._closed:
                raise RuntimeError("The session driver may create exactly one execution handler per progress call.")
            self._called = True

        handler = self._create_handler(task_request)
        handler.on_exit.once().subscribe(self._on_exit)
        return handler

    def validate(self) -> None:
        with self._lock:
            self._closed = True
            called = self._called
        if not called:
            raise RuntimeError("The session driver must create exactly one execution handler per progress call.")


class LLMSessionHandler:
    def __init__(self, id: LLMSessionID, *, manager: LLMSessionManager):
        self._id = id
        self._manager = manager

    @classmethod
    def create(cls, request: LLMSessionRequest, *, manager: LLMSessionManager | None = None) -> Self:
        manager = manager or GlobalPytoyContext.get().llm_session_manager
        session = LLMSession.from_request(request)
        manager.register(session)
        return cls(id=session.id, manager=manager)

    @classmethod
    def query(cls, query: LLMSessionQuery, *, manager: LLMSessionManager | None = None) -> Sequence[Self]:
        manager = manager or GlobalPytoyContext.get().llm_session_manager
        sessions = manager.select(query)
        return [cls(id=session.id, manager=manager) for session in sessions]

    @property
    def buffer_provider(self) -> LLMSessionBufferProvider:
        return self._require_session().buffer_provider

    @property
    def metadata(self) -> LLMSessionMetadata:
        return self._require_session().metadata

    @property
    def interface(self) -> LLMSessionInterfaceMode | None:
        return self._require_session().interface

    @property
    def driver(self) -> LLMSessionDriverProtocol:
        return self._require_session().driver

    def make_progress(self, user_prompt: str) -> Future[LLMExecutionExit[Any]]:
        """Dispatch progress and resolve on execution exit; wait only from a worker thread."""
        session = self._require_session()
        future: Future[LLMExecutionExit[Any]] = Future()
        completion_lock = Lock()

        def _set_result(exit_entity: LLMExecutionExit[Any]) -> None:
            with completion_lock:
                if not future.done():
                    future.set_result(exit_entity)

        def _set_exception(error: Exception) -> None:
            with completion_lock:
                if not future.done():
                    future.set_exception(error)

        def _dispatch() -> None:
            try:
                current_session = self._manager.get(self._id)
                if current_session is None:
                    raise ValueError(f"Session is already eliminated. `{self._id=}`")
                self._make_progress(current_session, user_prompt, _set_result)
            except Exception as error:
                _set_exception(error)
                raise

        backend_thread_dispatch(
            _dispatch,
            on_error=lambda error: session.logger.error(
                "Failed to dispatch LLM progress: %s",
                error,
                exc_info=(type(error), error, error.__traceback__),
            ),
        )
        return future

    def _make_progress(
        self,
        session: LLMSession,
        user_prompt: str,
        on_exit: Callable[[LLMExecutionExit[Any]], None],
    ) -> None:
        execution_creator = _SingleExecutionCreator(self.make_execution_handler, on_exit)
        session.driver.make_progress(
            execution_creator=execution_creator,
            llm_buffer_provider=session.buffer_provider,
            user_prompt=user_prompt,
        )
        execution_creator.validate()

    def make_execution_handler(self, task_request: TaskRequest) -> LLMExecutionHandler:
        session = self._require_session()
        if task_request.activity_sink is None:
            task_request = replace(
                task_request,
                activity_sink=LoggerActivitySink(session.logger),
            )
        task_execution_handler = session.task_session_handler.create_task(task_request)
        return LLMExecutionHandler.create_from_task_handler(
            task_execution_handler, kind=session.kind, logger=session.logger
        )

    def terminate(self) -> None:
        session = self._manager.remove(self._id)
        if session is None:
            return
        session.terminate()

    @property
    def on_exit(self) -> Event[LLMSessionExit]:
        return self._require_session().on_exit

    def _require_session(self) -> LLMSession:
        session = self._manager.get(self._id)
        if session is None:
            raise ValueError(f"Session is already eliminated. `{self._id=}`")
        return session
