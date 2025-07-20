import sys
from queue import Queue
from .protocol import TerminalBackendProtocol, ApplicationProtocol


class TerminalBackend(TerminalBackendProtocol):
    def __init__(self, impl: TerminalBackendProtocol):
        self._impl = impl

    @property
    def impl(self) -> TerminalBackendProtocol:
        return self._impl

    def start(
        self,
    ) -> None:
        """Start the terminal."""
        self.impl.start()

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
    def make_terminal(self, app: str | ApplicationProtocol = "C:\\Windows\\System32\\cmd.exe") -> TerminalBackend:
        def make_win32(app: str | ApplicationProtocol):
            from .impl_win import TerminalBackendWin
            from .application import ShellApplication
            from .line_buffers import LineBufferNaive
            line_buffer = LineBufferNaive()
            if isinstance(app, str):
                app = ShellApplication(app)
            impl = TerminalBackendWin(app, line_buffer)
            return TerminalBackend(impl)

        creators = {}
        creators["win32"] = make_win32
        creator = creators.get(sys.platform, None)
        if not creator:
            raise RuntimeError(f"TerminalBackend cannot be used in {sys.platform}")
        return creator(app)


if __name__ == "__main__":
    pass
