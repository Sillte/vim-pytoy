from pathlib import Path

from pytoy.shared.ui.pytoy_buffer import BufferSource
from pytoy.tool_execution.terminal.models import (
    BufferRequest,
    CommandExecutionWrapperType,
    TerminalDriverKind,
    TerminalDriverProtocol,
    TerminalExecutionHooks,
    TerminalExecutionQuery,
    TerminalExecutionRequest,
)

from .handler import TerminalExecutionHandler


class TerminalExecutionController:
    def __init__(
        self,
    ):
        pass

    def _to_driver_kind(self, driver: TerminalDriverKind | TerminalDriverProtocol) -> TerminalDriverKind:
        return driver.kind if isinstance(driver, TerminalDriverProtocol) else driver

    def send(
        self,
        driver: TerminalDriverKind | TerminalDriverProtocol,
        buffer_name: str | Path | BufferSource,
        content: str,
        *,
        command_wrapper: CommandExecutionWrapperType | None = None,
        cwd: Path | None = None,
    ) -> TerminalExecutionHandler:
        handler = self.get_or_create_handler(driver, buffer_name, command_wrapper=command_wrapper, cwd=cwd)
        handler.send(content)
        return handler

    def stop(self, buffer: str | BufferSource | Path | None = None):
        handlers = TerminalExecutionHandler.query(TerminalExecutionQuery.from_any(buffer))
        for handler in handlers:
            handler.stop()

    def terminate(self, buffer: str | Path | BufferSource | None = None) -> None:
        handlers = TerminalExecutionHandler.query(TerminalExecutionQuery.from_any(buffer))
        for handler in handlers:
            handler.terminate()

    def get_or_create_handler(
        self,
        driver: TerminalDriverKind | TerminalDriverProtocol,
        buffer_name: str | Path | BufferSource,
        *,
        hooks: TerminalExecutionHooks | None = None,
        command_wrapper: CommandExecutionWrapperType | None = None,
        cwd: Path | None = None,
    ) -> TerminalExecutionHandler:
        buffer_source = BufferSource.from_any(buffer_name)
        driver_kind = self._to_driver_kind(driver)
        query = TerminalExecutionQuery.from_any(buffer=buffer_source, kind=driver_kind)
        handlers = TerminalExecutionHandler.query(query=query)

        if handlers:
            handler = handlers[0]
        else:
            buffer_req = BufferRequest(source=buffer_source)
            execution_req = TerminalExecutionRequest(driver=driver, command_wrapper=command_wrapper, cwd=cwd)
            handler = TerminalExecutionHandler.create(request=execution_req, buffer_request=buffer_req)
            handler.start(hooks=hooks)
        return handler
