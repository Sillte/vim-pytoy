import threading
from collections.abc import Callable
from dataclasses import replace
from functools import wraps
from typing import Self, Sequence

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from pytoy.tool_execution.execution_environment import EnvironmentManager

from .factory import CommandExecutionFactory
from .manager import CommandExecutionManager
from .models import (
    BufferRequest,
    CommandExecutionContext,
    CommandExecutionHooks,
    CommandExecutionID,
    CommandExecutionKind,
    CommandExecutionQuery,
    CommandExecutionRequest,
    CommandExecutionStatus,
)


def assert_main_thread() -> None:
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError("This method must be called from the main thread.")


def main_thread_only[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        assert_main_thread()
        return func(*args, **kwargs)

    return wrapper


class CommandExecutionHandler:
    """Public handle for a command execution.

    Query results are best-effort observations rather than stable snapshots.
    An execution may finish and be removed from its manager immediately after
    a handler is returned, so callers must tolerate the handler becoming
    invalid.
    """

    def __init__(self, id: CommandExecutionID, *, manager: CommandExecutionManager) -> None:
        self._id = id
        self._manager = manager

    @classmethod
    @main_thread_only
    def create(
        cls,
        request: CommandExecutionRequest,
        buffer_request: BufferRequest,
        *,
        manager: CommandExecutionManager | None = None,
        environment_manager: EnvironmentManager | None = None,
    ) -> Self:
        if manager is None:
            manager = GlobalPytoyContext.get().command_execution_manager
        factory = CommandExecutionFactory(environment_manager=environment_manager)
        execution = factory.create(request, buffer_request=buffer_request)
        manager.register(execution)
        return cls(id=execution.id, manager=manager)

    @classmethod
    @main_thread_only
    def get_last_context(
        cls, kind: CommandExecutionKind, *, manager: CommandExecutionManager | None = None
    ) -> CommandExecutionContext | None:
        if manager is None:
            manager = GlobalPytoyContext.get().command_execution_manager
        return manager.get_last_context_by_kind(kind)

    @classmethod
    def query(
        cls, query: CommandExecutionQuery | None = None, *, manager: CommandExecutionManager | None = None
    ) -> Sequence[Self]:
        """Return best-effort handlers for executions matching the query."""
        query = query or CommandExecutionQuery()
        if manager is None:
            manager = GlobalPytoyContext.get().command_execution_manager
        executions = manager.select(query)
        return [cls(id=execution.id, manager=manager) for execution in executions]

    @main_thread_only
    def start(self, hooks: CommandExecutionHooks | None = None) -> None:
        hooks = hooks or CommandExecutionHooks.from_any()
        execution = self._manager.get(self._id)
        if execution is None:
            raise ValueError(f"`execution` does not exist; {self._id=}")
        if execution.status != "created":
            raise ValueError("`execution is not created status.")
        execution.start(hooks=hooks)

        context = CommandExecutionContext(
            buffer=execution.buffer_request,
            execution_request=replace(execution.execution_request, cwd=execution.cwd, env=execution.env),
            hooks=hooks,
            kind=execution.kind,
        )
        self._manager.register_context(context)

    @main_thread_only
    def terminate(self) -> None:
        execution = self._manager.get(self._id)
        if execution is None:
            raise ValueError(f"`execution` does not exist; {self._id=}")
        execution.terminate()

    @property
    def id(self) -> CommandExecutionID:
        return self._id

    @property
    def status(self) -> CommandExecutionStatus | None:
        execution = self._manager.get(self._id)
        if execution is None:
            return None
        return execution.status

    @property
    def stdout(self) -> PytoyBuffer:
        execution = self._manager.get(self._id)
        if execution is None:
            raise ValueError(f"`execution` does not exist; {self._id=}")
        return execution.stdout

    @property
    def stderr(self) -> PytoyBuffer | None:
        execution = self._manager.get(self._id)
        if execution is None:
            raise ValueError(f"`execution` does not exist; {self._id=}")
        return execution.stderr

    @property
    def command(self) -> str:
        """Resolved command,"""
        execution = self._manager.get(self._id)
        if execution is None:
            raise ValueError(f"`execution` does not exist; {self._id=}")
        if isinstance(execution.command, str):
            return execution.command
        return " ".join(execution.command)
