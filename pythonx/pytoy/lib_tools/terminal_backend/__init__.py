from queue import Queue
from .protocol import TerminalBackendProtocol


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

    def send(self, cmd: str):
        self.impl.send(cmd)

    @property
    def alive(self) -> bool:
        return self.impl.alive

    @property
    def busy(self) -> bool:
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


class TerminalBackendProvider:
    def make_terminal(self, command: str) -> TerminalBackend:
        import sys

        def make_win32():
            from .impl_win import TerminalBackendWin

            impl = TerminalBackendWin(command)
            return TerminalBackend(impl)

        creators = {}
        creators["win32"] = make_win32
        creator = creators.get(sys.platform, None)
        if not creator:
            raise RuntimeError(f"TerminalBackedn cannot be used in {sys.platform}")
        return creator()


if __name__ == "__main__":
    pass
