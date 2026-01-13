from queue import Queue
from pathlib import Path
from typing import Mapping
from .protocol import TerminalBackendProtocol, ApplicationProtocol, LineBufferProtocol


class TerminalBackend(TerminalBackendProtocol):
    def __init__(self, impl: TerminalBackendProtocol):
        self._impl = impl

    @property
    def impl(self) -> TerminalBackendProtocol:
        return self._impl

    def start(
        self, cwd: str | Path | None = None, env: Mapping[str, str] | None = None,
    ) -> None:
        """Start the terminal."""
        self.impl.start(cwd=cwd, env=env)

    def send(self, input_str: str):
        self.impl.send(input_str)

    @property
    def alive(self) -> bool:
        return self.impl.alive

    @property
    def busy(self) -> bool | None:
        return self.impl.busy

    def interrupt(self) -> None:
        """Stop the child process."""
        self.impl.interrupt()

    def terminate(self) -> None:
        """Kill the terminal."""
        self.impl.terminate()

    @property
    def queue(self) -> Queue:
        """It returns the queue which is used for output."""
        return self.impl.queue

    @property
    def last_line(self) -> str:
        return self.impl.last_line


class TerminalBackendProvider:
    def make_terminal(
        self,
        app: str | ApplicationProtocol | None = None,
        line_buffer: LineBufferProtocol | None = None,
    ) -> TerminalBackend:
        from .impl_main import TerminalBackendImplProvider

        impl = TerminalBackendImplProvider().provide(app=app, line_buffer=line_buffer)
        return TerminalBackend(impl)


if __name__ == "__main__":
    pass
