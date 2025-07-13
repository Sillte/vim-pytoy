"""Terminal, which is used by python.
"""
import time
from queue import Queue
from threading import Thread, Lock, RLock
import winpty

from .protocol import TerminalBackendProtocol
from .line_buffer import LineBuffer
from .win_utils import send_ctrl_c, find_children, force_kill


class TerminalBackendWin(TerminalBackendProtocol):
    def __init__(self, command: str = "C:\\Windows\\System32\\cmd.exe"):
        self._command = command

        self._queue = Queue()
        self._lock = RLock()
        self._proc: winpty.PtyProcess | None = None
        self._stdout_thread: Thread | None = None
        self._reading_stdout = False
        self._line_buffer = LineBuffer()

    def start(
        self,
    ) -> None:
        if self.alive:
            print("Already `started`.")
            return

        self._proc = winpty.PtyProcess.spawn(self._command)
        self._stdout_thread = Thread(target=self._stdout_loop, daemon=True)
        self._reading_stdout = True
        self._stdout_thread.start()

    @property
    def alive(self) -> bool:
        if not self._proc:
            return False
        return self._proc.isalive()

    @property
    def busy(self) -> bool:
        if not self._proc:
            return False
        if not self._proc.pid:
            return False
        return bool(find_children(self._proc.pid))
        

    def send(self, cmd: str):
        if not self.alive:
            self.start()
        assert self._proc is not None
        with self._lock:
            self._proc.write((cmd + "\r\n"))

    def interrupt(self) -> None:
        """Stop the child process."""
        if not self._proc:
            return 
        if not self._proc.pid:
            return
        for child in find_children(self._proc.pid):
            #force_kill(child)
            send_ctrl_c(child)

    def terminate(self) -> None:
        """Kill the terminate."""
        if not self._proc:
            return
        self._proc.terminate(force=True)

    @property
    def queue(self) -> Queue:
        """It returns the queue which is used for output."""
        return self._queue

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
                self.queue.put(lines)


if __name__ == "__main__":
    pass
