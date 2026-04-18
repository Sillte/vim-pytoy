from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Mapping, Any, Self

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.job_execution.command_executor.executor import CommandExecutor
from pytoy.job_execution.command_executor.launcher.quickfix import QuickfixProfile
from pytoy.job_execution.command_executor.launcher.quickfix import make_quickfix_hooks
from pytoy.job_execution.command_executor.manager import CommandExecutionManager
from pytoy.job_execution.command_executor.models import BufferRequest, ExecutionHooks, ExecutionKind, ExecutionQuery, ExecutionRequest, PostProcessContext, ExecutionWrapperType, ExecutionContext
from pytoy.job_execution.utils import get_current_directory
from pytoy.shared.ui import BufferSource, PytoyBuffer


@dataclass(frozen=True)
class LaunchProfile:
    kind: ExecutionKind = "$default"
    command_wrapper: ExecutionWrapperType | None = "auto"
    execution_hooks: ExecutionHooks | None = None
    
    @classmethod
    def from_str(cls, arg: Any) -> Self:
        return cls(kind=arg)

    

def _hide_empty_error_buffer(post_process_context: PostProcessContext) -> None:
    stderr = post_process_context.stderr
    if stderr:
        if not stderr.content.strip():
            stderr.hide()

DefaultHooks = ExecutionHooks(on_post_process=_hide_empty_error_buffer)


class CommandLauncher:
    def __init__(self, launch_profile: LaunchProfile | ExecutionKind, *, execution_manager: CommandExecutionManager | None = None):
        if not execution_manager:
            execution_manager = GlobalPytoyContext.get().command_execution_manager
        if isinstance(launch_profile, str):
            launch_profile = LaunchProfile.from_str(launch_profile)

        self._execution_manager = execution_manager
        self._launch_profile = launch_profile

    @property
    def execution_manager(self) -> CommandExecutionManager:
        return self._execution_manager

    @property
    def launch_profile(self) -> LaunchProfile:
        return self._launch_profile
    
    @property
    def last_context(self) -> ExecutionContext | None:
        return self.execution_manager.get_last_context_by_kind(self.launch_profile.kind)

    def run(self,
            command: str | list[str],
            stdout: PytoyBuffer | BufferSource | str | Path,
            stderr: PytoyBuffer | BufferSource | str | Path | None = None,
            *,
            cwd: str | Path | None = None,
            meta: Mapping[str, Any] | None = None,
            init_buffer: bool = True
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
        execution_request = ExecutionRequest(command=command, cwd=cwd, command_wrapper=self.launch_profile.command_wrapper, kind=kind, meta=meta)
        execution_hooks = profile.execution_hooks or self.default_execution_hooks
        self._send_request(buffer_request, execution_request, execution_hooks, init_buffer=init_buffer)

    @property
    def default_execution_hooks(self) -> ExecutionHooks:
        return DefaultHooks

    def rerun(self, stdout: PytoyBuffer | BufferSource | str | Path,
                    stderr: PytoyBuffer | BufferSource | str | Path | None = None, *,
                    init_buffer: bool = True):
        command_kind = self.launch_profile.kind

        stdout = stdout.source if isinstance(stdout, PytoyBuffer) else BufferSource.from_any(stdout)
        if stderr is not None:
            stderr = stderr.source if isinstance(stderr, PytoyBuffer) else BufferSource.from_any(stderr)
        buffer_request = BufferRequest(stdout=stdout, stderr=stderr)
        last_context = self.execution_manager.get_last_context_by_kind(command_kind)
        if not last_context:
            raise RuntimeError(f"Previous execution for `{command_kind=}` does not exist.")
        execution_request = last_context.execution_request
        execution_hooks = last_context.hooks
        cwd = execution_request.cwd
        if cwd is None:
            raise RuntimeError("Violation of `last_context`, `cwd` is None.")

        self._send_request(buffer_request, execution_request, execution_hooks, init_buffer=init_buffer)

    def stop(self):
        query = ExecutionQuery(kind=self.launch_profile.kind)
        for execution in self.execution_manager.select(query):
            execution.runner.terminate()


    @property
    def is_running(self) -> bool:
        query = ExecutionQuery(kind=self.launch_profile.kind)
        return bool(self.execution_manager.select(query=query))


    def _send_request(self, buffer_request: BufferRequest, execution_request: ExecutionRequest, execution_hooks: ExecutionHooks, *, init_buffer: bool = True):
        command_executor = CommandExecutor(buffer_request)
        command_executor.execute(execution_request, init_buffer=init_buffer, hooks=execution_hooks)