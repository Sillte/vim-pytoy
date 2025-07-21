"""Terminal, which is used by python.
"""
import time 
from queue import Queue, Empty
from threading import Thread, Lock
import winpty

from .protocol import TerminalBackendProtocol, ApplicationProtocol, LineBufferProtocol, LINE_WAITTIME
from .line_buffers.line_buffer_naive import LineBufferNaive
from .utils import find_children  


class TerminalBackendWin(TerminalBackendProtocol):
    def __init__(self, app: ApplicationProtocol, line_buffer: LineBufferProtocol | None = None):
        if line_buffer is None:
            line_buffer = LineBufferNaive()

        self._app = app

        self._queue = Queue()
        self._lock = Lock()
        self._proc: winpty.PtyProcess | None = None
        self._stdout_thread: Thread | None = None
        self._stdin_thread: Thread | None = None
        self._stdin_queue = Queue()
        self._line_buffer = line_buffer
        self._last_line = ""
        self._running = False

    def start(
        self,
    ) -> None:
        if self.alive:
            print("Already `started`.")
            return
        with self._lock:
            self._proc = winpty.PtyProcess.spawn(self._app.command, dimensions=(self._line_buffer.lines, self._line_buffer.columns))
            _focus_assure()

            self._stdout_thread = Thread(target=self._stdout_loop, daemon=True)
            self._stdin_thread = Thread(target=self._stdin_loop, daemon=True)
            self._running = True
            self._stdout_thread.start()
            self._stdin_thread.start()

    @property
    def alive(self) -> bool:
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
        lines = self._app.make_lines(input_str)

        for line in lines:
            if isinstance(line, str):
                if not (line.endswith("\r") or line.endswith("\n")):
                    line = line + "\r\n"
            self._stdin_queue.put(line)

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
        with self._lock:
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

    def _stdin_loop(self):
        while self.alive and self._running:
            if not self._proc:
                self._running = False
                continue
            try:
                line = self._stdin_queue.get(timeout=0.5)
            except Empty:
                continue
            if isinstance(line, (int, float)):
                time.sleep(line)
                continue
            else:  # type(line) is str
                try:
                    if self._proc is None:
                        self._running = False
                        continue
                    self._proc.write(line)
                except EOFError:
                    self._running = False
                    continue
                else:
                    time.sleep(0.01)


    def _stdout_loop(self):
        while self.alive and self._running:
            if not self._proc:
                self._running = False
                continue
            try:
                chunk = self._proc.readline()
            except EOFError:
                self._running = False
                chunk = None

            #print("chunk", chunk)
            if chunk:
                lines = self._line_buffer.feed(chunk)
            else:
                lines = []

            if lines:
                self._last_line = lines[-1]
                self.queue.put(lines)

        lines = self._line_buffer.flush()
        # [NOTE] For the last resort, only the meaningful line are `put` into queue.
        lines = [line for line in lines if line.strip()]
        if lines:
            self._last_line = lines[-1]
            self.queue.put(lines)

def _focus_assure():
    import vim
    is_gui = vim.eval('has("gui_running")')
    if is_gui:
        from .win_utils import focus_gvim
        focus_gvim()


if __name__ == "__main__":
    pass
