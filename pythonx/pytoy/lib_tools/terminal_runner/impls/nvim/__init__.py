from __future__ import annotations
import vim
import time
from pathlib import Path
from queue import Queue, Empty
from threading import Thread
from typing import Any, Sequence

from pyte import Screen, Stream
from pytoy.lib_tools.terminal_runner.models import (
    TerminalJobProtocol,
    TerminalJobRequest,
    TerminalDriverProtocol,
    SpawnOption,
    ConsoleSnapshot,
    Snapshot,
    WaitOperation,
    InputOperation,
    JobEvents,
    JobID
)
from pytoy.infra.core.models import CursorPosition
from pytoy.infra.vim_function import PytoyVimFunctions
from pytoy.infra.events import EventEmitter
from pytoy.lib_tools.process_utils import find_children_pids


class InputSolverTask:
    def __init__(self, job_id: int, driver: TerminalDriverProtocol):
        self.job_id = job_id
        self.driver = driver
        self.queue: Queue[InputOperation | None] = Queue()
        self.alive = True
        self.eof = "\r"

    def send(self, input_str: str) -> None:
        ops = self.driver.make_lines(input_str)
        for op in ops:
            print("op", op)
            self.queue.put(op)

    def loop(self) -> None:
        """Background thread loop for input processing"""
        while self.alive:
            try:
                op = self.queue.get(timeout=1.0)
            except Empty:
                continue

            if op is None: # Exit signal
                break

            try:
                if isinstance(op, str):
                    # Protocol: Append the appropriate `CR`.  
                    #suffix = "" if (op.endswith("\r") or op.endswith("\n")) else "\n"
                    #clean_op = op.rstrip("\r\n")
                    payload = op + self.eof
                    #payload = op + suffix
                    # Safety: Use threadsafe_call for Neovim API from background thread
                    vim.session.threadsafe_call(
                        lambda: vim.call('chansend', self.job_id, op + " ")
                    )
                    import time
                    time.sleep(0.1)

                    vim.session.threadsafe_call(
                        lambda: vim.call('chansend', self.job_id, self.eof)
                    )
                elif isinstance(op, WaitOperation):
                    time.sleep(op.time)
            except Exception:
                pass
            finally:
                self.queue.task_done()


class TerminalJobNvim(TerminalJobProtocol):
    def __init__(self, request: TerminalJobRequest, spawn_option: SpawnOption | None = None):
        self._request = request
        self._spawn_option = spawn_option or SpawnOption()
        self._driver = request.driver
        self._job_id: int | None = None

        # VT100 Emulation via pyte
        cols = self._request.console.cols or 80
        rows = self._request.console.lines or 24
        self._screen = Screen(cols, rows)
        self._stream = Stream(self._screen)

        # Emitters
        self._update_emitter = EventEmitter[int]()
        self._exit_emitter = EventEmitter[Any]()
        self._events = JobEvents(
            on_update=self._update_emitter.event,
            on_job_exit=self._exit_emitter.event
        )

        self._start()

    def _start(self) -> None:
        # 1. Setup Callbacks
        self._on_out_name = PytoyVimFunctions.register(self._on_vim_output, prefix="NvimTTYOut")
        self._on_exit_name = PytoyVimFunctions.register(self._on_vim_exit, prefix="NvimTTYExit")

        # 2. Options for jobstart
        options = {
            'pty': True,
            'width': self._screen.columns,
            'height': self._screen.lines,
            'on_stdout': self._on_out_name,
            'on_stderr': self._on_out_name,
            'on_exit': self._on_exit_name,
            'stdout_buffered': False
        }

        if self._spawn_option.cwd:
            options["cwd"] = str(Path(self._spawn_option.cwd).absolute().as_posix())
        if self._spawn_option.env:
            options["env"] = self._spawn_option.env

        # 3. Launch
        self._job_id = int(vim.call('jobstart', self._driver.command, options))
        if self._job_id <= 0:
            raise RuntimeError(f"Neovim jobstart failed: {self._job_id}")

        # 4. Input Thread
        self._input_task = InputSolverTask(self._job_id, self._driver)
        self._input_thread = Thread(target=self._input_task.loop, daemon=True)
        self._input_thread.start()

    def _on_vim_output(self, job_id: int, data: list[str], event: str) -> None:
        # Neovim provides data as a list of lines. Join them with CRLF for the emulator.
        # Pyte accepts only the stream. 

        # NeovimのdataリストをPTYの改行コードで結合
        #chunk = "\r\n".join(data)
        #self._stream.feed(chunk)
        print("data", data)
        n_lines = len(data)
        for i, line in enumerate(data):
            if i + 1 == n_lines:
                if line:
                    self._stream.feed(line)
            else:
                self._stream.feed(line + "\n")
        self._update_emitter.fire(job_id)

    def _on_vim_exit(self, job_id: int, exit_code: int, event: str) -> None:
        self._exit_emitter.fire(exit_code)
        self.dispose()

    def send(self, input: str) -> None:
        if self.alive:
            print("input", input)
            self._input_task.send(input)

    def interrupt(self) -> None:
        if self.alive:
            self._driver.interrupt(self.pid, self.children_pids)

    def terminate(self) -> None:
        if self._job_id is not None:
            vim.call('jobstop', self._job_id)
            self._job_id = None

    def dispose(self) -> None:
        self.terminate()
        # Cleanup input thread
        self._input_task.alive = False
        self._input_task.queue.put(None) 
        
        PytoyVimFunctions.deregister(self._on_out_name)
        PytoyVimFunctions.deregister(self._on_exit_name)
        self._update_emitter.dispose()
        self._exit_emitter.dispose()

    @property
    def snapshot(self) -> Snapshot:
        # pyte.screen.display returns a list of visible lines
        content = "\n".join(self._screen.display)
        
        return Snapshot(
            timestamp=time.time(),
            console=ConsoleSnapshot(
                lines=self._screen.lines,
                cols=self._screen.columns,
                content=content
            ),
            cursor=CursorPosition(
                line=self._screen.cursor.y,
                col=self._screen.cursor.x
            )
        )

    @property
    def alive(self) -> bool:
        if self._job_id is None: return False
        # In Neovim, jobwait with timeout 0 returns -1 if still running
        return vim.call('jobwait', [self._job_id], 0)[0] == -1

    @property
    def pid(self) -> int:
        if self._job_id is None: return -1
        try:
            return int(vim.call('jobpid', self._job_id))
        except Exception:
            return -1

    @property
    def children_pids(self) -> list[int]:
        p = self.pid
        return find_children_pids(p) if p > 0 else []

    @property
    def job_id(self) -> JobID | None:
        return self._job_id

    @property
    def name(self) -> str:
        return self._request.name

    @property
    def cwd(self) -> Path:
        return Path(self._spawn_option.cwd or Path.cwd())

    @property
    def events(self) -> JobEvents:
        return self._events
