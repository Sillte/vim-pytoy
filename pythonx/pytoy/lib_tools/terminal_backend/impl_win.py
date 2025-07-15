"""Terminal, which is used by python.
"""
from queue import Queue
from threading import Thread, Lock
import winpty

from .protocol import TerminalBackendProtocol, ApplicationProtocol
from .line_buffer import LineBuffer
from .utils import find_children  


class TerminalBackendWin(TerminalBackendProtocol):
    def __init__(self, app: ApplicationProtocol):
        self._app = app

        self._queue = Queue()
        self._lock = Lock()
        self._proc: winpty.PtyProcess | None = None
        self._stdout_thread: Thread | None = None
        self._reading_stdout = False
        self._line_buffer = LineBuffer()
        self._last_line = ""

    def start(
        self,
    ) -> None:
        if self.alive:
            print("Already `started`.")
            return
        with self._lock:
            self._proc = winpty.PtyProcess.spawn(self._app.command)
            self._stdout_thread = Thread(target=self._stdout_loop, daemon=True)
            self._reading_stdout = True
            self._stdout_thread.start()

    @property
    def alive(self) -> bool:
        with self._lock:
            if not self._proc:
                return False
            return self._proc.isalive()

    @property
    def busy(self) -> bool | None:
        if not self._proc:
            return False
        if not self._proc.pid:
            return False
        children_pids = find_children(self._proc.pid)
        return self._app.is_busy(children_pids, self.last_line)
        

    def send(self, input_str: str):
        if not self.alive:
            self.start()
        assert self._proc is not None
        input_str = self._app.modify(input_str)
        self._proc.write(input_str)

    def interrupt(self) -> None:
        """Stop the child process."""
        if not self._proc:
            return 
        if not self._proc.pid:
            return
        pid = self._proc.pid
        children_pids = find_children(self._proc.pid)
        self._app.interrupt(pid, children_pids)


    def terminate(self) -> None:
        """Kill the terminate."""
        if not self._proc:
            return
        self._proc.terminate(force=True)

    @property
    def queue(self) -> Queue:
        """It returns the queue which is used for output."""
        return self._queue

    @property
    def last_line(self) -> str:
        """It returns the lastest line added to queue."""
        return self._last_line

    def _stdout_loop(self):
        while self.alive and self._reading_stdout:
            if not self._proc:
                self._reading_stdout = False
                continue

            try:
                chunk = self._proc.read(1024)
            except EOFError:
                self._reading_stdout = False
                chunk = None

            if chunk:
                lines = self._line_buffer.append(chunk)
            else:
                lines = []

            if lines:
                self._last_line = lines[-1]
                self.queue.put(lines)


if __name__ == "__main__":
    pass
