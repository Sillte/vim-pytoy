from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from pytoy.tool_execution.command.infra import CommandRunner
from pytoy.tool_execution.command.manager import CommandExecutionManager
from pytoy.tool_execution.command.models import (
    BufferRequest,
    CommandExecutionHooks,
    CommandExecutionRequest,
)

from .factory import CommandExecutionFactory
from .handler import CommandExecutionHandler


class CommandExecutor:
    def __init__(self, buffer_request: BufferRequest | str, *, ctx: GlobalPytoyContext | None = None):
        if isinstance(buffer_request, str):
            buffer_request = BufferRequest.from_str(buffer_request)
        if ctx is None:
            from pytoy.contexts.pytoy import GlobalPytoyContext

            ctx = GlobalPytoyContext.get()
        self._ctx = ctx
        self._execution_manager: CommandExecutionManager = ctx.command_execution_manager
        self._environment_manager = ctx.core_context.environment_manager
        self._buffer_request = buffer_request
        self._stdout, self._stderr = CommandRunner.solve_buffers(buffer_request.stdout, buffer_request.stderr)

    @property
    def execution_manager(self) -> CommandExecutionManager:
        return self._execution_manager

    @property
    def stdout(self) -> PytoyBuffer:
        return self._stdout

    @property
    def stderr(self) -> PytoyBuffer | None:
        return self._stderr

    def execute(
        self, request: CommandExecutionRequest, hooks: CommandExecutionHooks | None = None, *, init_buffer: bool = True
    ) -> CommandExecutionHandler:
        factory = CommandExecutionFactory(environment_manager=self._environment_manager)
        execution = factory.create(request, self._buffer_request)
        self._execution_manager.register(execution)

        if init_buffer:
            execution.stdout.init_buffer()
            if execution.stderr:
                execution.stderr.init_buffer()

        handler = CommandExecutionHandler(id=execution.id, manager=self._execution_manager)
        hooks = hooks or CommandExecutionHooks()
        handler.start(hooks=hooks)
        return handler


if __name__ == "__main__":
    pass
