"""Terminal, which is used by python.
"""
import sys
import time 
from pathlib import Path
from queue import Queue, Empty
from threading import Thread, Lock

from .protocol import TerminalBackendProtocol, ApplicationProtocol, LineBufferProtocol, PseudoTerminalProtocol, PseudoTerminalProviderProtocol
from .line_buffers.line_buffer_naive import LineBufferNaive
from .utils import find_children


class TerminalBackendMain(TerminalBackendProtocol):
    def __init__(self, app: ApplicationProtocol, pseudo_provider: PseudoTerminalProviderProtocol, line_buffer: LineBufferProtocol | None = None):
        if line_buffer is None:
            line_buffer = LineBufferNaive()

        self._app = app
        self._pseudo_provider = pseudo_provider
        self._line_buffer = line_buffer

        self._queue = Queue()
        self._lock = Lock()
        self._proc: PseudoTerminalProviderProtocol | None = None
        self._stdout_thread: Thread | None = None
        self._stdin_thread: Thread | None = None
        self._stdin_queue = Queue()
        self._last_line = ""
        self._running = False

    def start(
        self,
        cwd: str | Path | None = None, 
        env: dict[str, str] | None = None
    ) -> None:
        if self.alive:
            print("Already `started`.")
            return
        with self._lock:
            self._proc = self._pseudo_provider.spawn(self._app.command, dimensions=(self._line_buffer.lines, self._line_buffer.columns), cwd=cwd, env=env)
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
            #self._proc.terminate(force=True)
            self._proc.terminate()

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

            if lines and "\n".join(lines):
                lines = self._app.filter(lines)
                self._last_line = lines[-1]
                self.queue.put(lines)

        lines = self._line_buffer.flush()
        # [NOTE] For the last resort, only the meaningful line are `put` into queue.
        lines = [line for line in lines if line.strip()]
        if lines:
            self._last_line = lines[-1]
            self.queue.put(lines)


class TerminalBackendImplProvider:
    def __init__(self):
        pass

    def provide(self, app: str | ApplicationProtocol | None = None, line_buffer: LineBufferProtocol | None = None) -> TerminalBackendProtocol: 
        from .application import ShellApplication, DEFAULT_SHELL_APPLICATION_NAME
        from .line_buffers import LineBufferNaive
        def make_win32() -> PseudoTerminalProviderProtocol:
            from .impl_win import PseudoTerminalProviderWin
            return PseudoTerminalProviderWin()

        def make_linux():
            from .impl_unix import PseudoTerminalProviderUnix
            return PseudoTerminalProviderUnix()
            

        if not line_buffer: 
            line_buffer = LineBufferNaive()
        if app is None:
            app = DEFAULT_SHELL_APPLICATION_NAME
        if isinstance(app, str):
            app = ShellApplication(app)

        creators = {}
        creators["win32"] = make_win32
        creators["linux"] = make_linux
        creator = creators.get(sys.platform, None)
        if not creator:
            raise RuntimeError(f"TerminalBackend cannot be used in {sys.platform}")
        pseudo_provider = creator()
        return TerminalBackendMain(app, pseudo_provider=pseudo_provider, line_buffer=line_buffer)


def _focus_assure():
    import vim
    import sys
    is_gui = vim.eval('has("gui_running")')
    if is_gui:
        if sys.platform == "win32":
            from .win_utils import focus_gvim
            focus_gvim()
    # In case of `gui` or `linux`, this operation is not necessary.


if __name__ == "__main__":
    pass
