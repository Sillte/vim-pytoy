import threading
from functools import wraps
from pathlib import Path
from typing import Callable

from pytoy.shared.ui.pytoy_buffer import BufferSource

from .handler import TerminalExecutionHandler
from .models import (
    BufferRequest,
    CommandWrapperType,
    TerminalDriverKind,
    TerminalDriverProtocol,
    TerminalExecutionQuery,
    TerminalExecutionRequest,
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


class TerminalExecutionController:
    @main_thread_only
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
        command_wrapper: CommandWrapperType | None = None,
        cwd: Path | None = None,
    ) -> TerminalExecutionHandler:
        handler = self.get_or_create_handler(driver, buffer_name, command_wrapper=command_wrapper, cwd=cwd)
        if handler.status == "created":
            handler.start()
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

    @main_thread_only
    def get_or_create_handler(
        self,
        driver: TerminalDriverKind | TerminalDriverProtocol,
        buffer_name: str | Path | BufferSource,
        *,
        command_wrapper: CommandWrapperType | None = None,
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
        return handler
