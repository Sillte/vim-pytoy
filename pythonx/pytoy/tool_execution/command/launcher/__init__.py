from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Self

from pytoy.job_execution.utils import get_current_directory
from pytoy.shared.ui import BufferSource, PytoyBuffer
from pytoy.tool_execution.command import CommandExecutionHandler, CommandExecutionQuery
from pytoy.tool_execution.command.models import (
    BufferRequest,
    CommandExecutionContext,
    CommandExecutionHooks,
    CommandExecutionKind,
    CommandExecutionRequest,
    CommandExecutionResolvedParam,
    CommandExecutionResult,
    CommandWrapperTypeLike,
)


@dataclass(frozen=True)
class LaunchProfile:
    kind: CommandExecutionKind = "$default"
    command_wrapper: CommandWrapperTypeLike | None = "auto"
    execution_hooks: CommandExecutionHooks | None = None

    @classmethod
    def from_str(cls, arg: Any) -> Self:
        return cls(kind=arg)


def hide_empty_error_buffer(result: CommandExecutionResult) -> None:
    stderr_buffer = result.stderr_buffer
    if stderr_buffer:
        if not stderr_buffer.content.strip():
            stderr_buffer.hide()


def append_command_hook(resolved_param: CommandExecutionResolvedParam) -> None:
    command = resolved_param.command
    resolved_param.stdout_buffer.append(command)


def get_default_hooks() -> CommandExecutionHooks:
    return CommandExecutionHooks(on_start=append_command_hook, on_result=hide_empty_error_buffer)


class CommandLauncher:
    def __init__(self, launch_profile: LaunchProfile | CommandExecutionKind):
        if isinstance(launch_profile, str):
            launch_profile = LaunchProfile.from_str(launch_profile)

        self._launch_profile = launch_profile

    @property
    def launch_profile(self) -> LaunchProfile:
        return self._launch_profile

    @property
    def last_context(self) -> CommandExecutionContext | None:
        return CommandExecutionHandler.get_last_context(self.launch_profile.kind)

    def run(
        self,
        command: str | list[str],
        stdout: PytoyBuffer | BufferSource | str | Path,
        stderr: PytoyBuffer | BufferSource | str | Path | None = None,
        *,
        cwd: str | Path | None = None,
        meta: Mapping[str, Any] | None = None,
        init_buffer: bool = True,
    ):
        meta = meta or {}
        kind = self.launch_profile.kind
        if self.is_running:
            raise ValueError(f"Already `{kind=}` is running.")

        cwd = Path(cwd) if cwd else get_current_directory()
        profile = self.launch_profile
        stdout = stdout.source if isinstance(stdout, PytoyBuffer) else BufferSource.from_any(stdout)
        if stderr is not None:
            stderr = stderr.source if isinstance(stderr, PytoyBuffer) else BufferSource.from_any(stderr)

        buffer_request = BufferRequest(stdout=stdout, stderr=stderr)
        execution_request = CommandExecutionRequest(
            command=command, cwd=cwd, command_wrapper=self.launch_profile.command_wrapper, kind=kind, meta=meta
        )
        execution_hooks = profile.execution_hooks or self.default_execution_hooks
        self._send_request(buffer_request, execution_request, execution_hooks, init_buffer=init_buffer)

    @property
    def default_execution_hooks(self) -> CommandExecutionHooks:
        return get_default_hooks()

    def rerun(
        self,
        stdout: PytoyBuffer | BufferSource | str | Path,
        stderr: PytoyBuffer | BufferSource | str | Path | None = None,
        *,
        init_buffer: bool = True,
    ):
        command_kind = self.launch_profile.kind

        stdout = stdout.source if isinstance(stdout, PytoyBuffer) else BufferSource.from_any(stdout)
        if stderr is not None:
            stderr = stderr.source if isinstance(stderr, PytoyBuffer) else BufferSource.from_any(stderr)
        buffer_request = BufferRequest(stdout=stdout, stderr=stderr)
        last_context = CommandExecutionHandler.get_last_context(command_kind)
        if not last_context:
            raise RuntimeError(f"Previous execution for `{command_kind=}` does not exist.")
        execution_request = last_context.execution_request
        execution_hooks = last_context.hooks
        cwd = execution_request.cwd
        if cwd is None:
            raise RuntimeError("Violation of `last_context`, `cwd` is None.")

        self._send_request(buffer_request, execution_request, execution_hooks, init_buffer=init_buffer)

    def stop(self):
        query = CommandExecutionQuery(kind=self.launch_profile.kind)
        handlers = CommandExecutionHandler.query(query)
        for handler in handlers:
            handler.terminate()

    @property
    def is_running(self) -> bool:
        query = CommandExecutionQuery(kind=self.launch_profile.kind)
        handlers = CommandExecutionHandler.query(query)
        return bool(handlers)

    def _send_request(
        self,
        buffer_request: BufferRequest,
        execution_request: CommandExecutionRequest,
        execution_hooks: CommandExecutionHooks,
        *,
        init_buffer: bool = True,
    ) -> CommandExecutionHandler:
        handler = CommandExecutionHandler.create(execution_request, buffer_request=buffer_request)
        if init_buffer:
            handler.stdout.init_buffer()
            if handler.stderr:
                handler.stderr.init_buffer()
        handler.start(hooks=execution_hooks)
        return handler
