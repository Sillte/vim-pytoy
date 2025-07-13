from pytoy.ui import PytoyBuffer
from pytoy.ui.pytoy_buffer.queue_updater import QueueUpdater
from pytoy.lib_tools.terminal_backend import TerminalBackend, TerminalBackendProvider


class TerminalExecutor:
    def __init__(self, buffer: PytoyBuffer, terminal_backend: TerminalBackend):
        self._buffer = buffer
        self._backend = terminal_backend
        self._updater: None | QueueUpdater = None

    @property
    def buffer(self) -> PytoyBuffer:
        return self._buffer

    @property
    def backend(self) -> TerminalBackend:
        return self._backend

    @property
    def updater(self) -> QueueUpdater | None:
        return self._updater


    def start(self, ):
        if self.alive:
            print("Already running")
            return 
        queue = self.backend.queue
        self.backend.start()
        self._updater = QueueUpdater(self.buffer, queue)
        self._updater.register()

    def send(self, cmd: str):
        self.backend.send(cmd)

    @property
    def alive(self) -> bool: 
        return self.backend.alive

    @property
    def busy(self) -> bool: 
        """Whether the somework is performed or not.
        """
        return self.backend.busy

    def interrupt(self) -> None:
        """Stop the child process.
        """
        self.backend.interrupt()

    def terminate(self) -> None:
        """Kill the terminal.
        """
        if not self.alive:
            print("Already terminated.")
            return 

        self.backend.terminate()
        assert self.updater 
        self.updater.deregister()
