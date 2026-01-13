from __future__ import annotations
import vim
import time
import json
from pathlib import Path
from typing import Any, Sequence

from pytoy.lib_tools.terminal_runner.models import (
    TerminalJobProtocol,
    TerminalJobRequest,
    SpawnOption,
    ConsoleSnapshot,
    Snapshot,
    WaitOperation,
    WaitUntilOperation, 
    RawStr, 
    LineStr,
    InputOperation,
    JobEvents,
    JobID
)

from pytoy.lib_tools.terminal_runner.impls.core import TerminalJobCore
from pytoy.infra.core.models import CursorPosition
from pytoy.infra.vim_function import PytoyVimFunctions
from pytoy.infra.events import EventEmitter
from pytoy.lib_tools.process_utils import find_children_pids

class TerminalJobVim(TerminalJobProtocol):
    def __init__(self, request: TerminalJobRequest, spawn_option: SpawnOption | None = None):
        self._request = request
        self._spawn_option = spawn_option or SpawnOption()
        self._driver = request.driver
        self._bufnr: int = -1
        self._core = TerminalJobCore(self._request, self._spawn_option)   
        
        self._start()

    def _start(self) -> None:
        # 1. Register global Vim functions for callbacks
        self._on_exit_name = PytoyVimFunctions.register(self._on_vim_exit, prefix="VimTTYExit")
        self._on_out_name = PytoyVimFunctions.register(self._on_vim_output, prefix="VimTTYOut")

        # 2. Build term_start options
        cols = self._request.console.cols or 80
        rows = self._request.console.lines or 24
        
        options = {
            "hidden": 1,
            "term_cols": cols,
            "term_rows": rows,
            "out_cb": self._on_out_name,
            "err_cb": self._on_out_name,
            "exit_cb": self._on_exit_name,
            "norestore": 1,
        }

        if self._spawn_option.cwd:
            options["cwd"] = str(Path(self._spawn_option.cwd).absolute().as_posix())
        if self._spawn_option.env:
            options["env"] = self._spawn_option.env

        # 3. Launch terminal via vim.eval with JSON strings
        cmd_json = json.dumps(self._driver.command)
        opt_json = json.dumps(options)
        self._bufnr = int(vim.eval(f"term_start({cmd_json}, {opt_json})"))
        
        if self._bufnr <= 0:
            raise RuntimeError(f"Vim term_start failed: {self._bufnr}")

    def _on_vim_output(self, channel: Any, data: Any) -> None:
        self._core.update_emitter.fire(self._bufnr)

    def _on_vim_exit(self, job: Any, exit_status: int) -> None:
        self._core.exit_emitter.fire(exit_status)
        self.dispose()

    def _send_operations(self, operations: Sequence[InputOperation]) -> None:

        eol = self._driver.eol 
        enter_eol = eol if eol else TerminalJobCore.get_default_eol()
        snapshot_getter = (lambda : self.snapshot)
        for op in operations:
            payload = TerminalJobCore.deal_operation(op, enter_eol, snapshot_getter)

            if payload is not None:
                input_json = json.dumps(payload)
                vim.command(f"call term_sendkeys({self._bufnr}, {input_json})")

    def send(self, input: str) -> None:
        if not self.alive:
            return
        operations: Sequence[InputOperation] = self._driver.make_operations(input)
        self._send_operations(operations)
        
    def interrupt(self) -> None:
        if self.alive:
            i_code = self._driver.interrupt(self.pid, self.children_pids)
            if not i_code:
                return 
            match i_code.preference:
                case  "sigint":
                    self._send_operations([RawStr("\x03")])
                case  "kill_tree":
                    TerminalJobCore.kill_processes(self.children_pids)

    def terminate(self) -> None:
        if self.alive:
            # Get job from bufnr then stop
            vim.command(f"call job_stop(term_getjob({self._bufnr}))")
            self._on_vim_exit(None, 1) # Note: Abnormal.
        # Note: abnormal. hack.
        # Since some times, `_on_vim_exist` is not called when `job_stop` is used.
        self.dispose()


    def dispose(self) -> None:
        if self._bufnr > 0:
            # Check buffer existence before deleting
            if vim.eval(f"bufexists({self._bufnr})") == "1":
                vim.command(f"bdelete! {self._bufnr}")
            self._bufnr = -1

        self._core.update_emitter.dispose()
        self._core.exit_emitter.dispose()
            
        # Asyncronous hack is important, since this must be called after `Job` `on_exit` is called.
        from pytoy.infra.timertask import TimerTask 
        def _inner():
            PytoyVimFunctions.deregister(self._on_exit_name)
            PytoyVimFunctions.deregister(self._on_out_name)
        TimerTask.execute_oneshot(_inner, interval=0)

    @property
    def snapshot(self) -> Snapshot:
        if self._bufnr <= 0:
            return Snapshot(
                timestamp=time.time(),
                console=ConsoleSnapshot(0, 0, ""),
                cursor=CursorPosition(0, 0)
            )

        # Get visual buffer lines
        vim.command(f"call term_wait({self._bufnr}, 10)")
        size = vim.eval(f"term_getsize({self._bufnr})")
        rows = int(size[0])
        lines = [ vim.eval(f'term_getline({self.job_id}, {i + 1})') for i in range(rows) ]
        
        # Get terminal state via eval
        cursor = vim.eval(f"term_getcursor({self._bufnr})") # returns ["row", "col"]
        size = vim.eval(f"term_getsize({self._bufnr})")     # returns ["rows", "cols"]

        return Snapshot(
            timestamp=time.time(),
            console=ConsoleSnapshot(
                lines=int(size[0]),
                cols=int(size[1]),
                content="\n".join(lines)
            ),
            cursor=CursorPosition(
                line=int(cursor[0]) - 1, 
                col=int(cursor[1]) - 1
            )
        )

    @property
    def alive(self) -> bool:
        if self._bufnr <= 0: return False
        return vim.eval(f"job_status(term_getjob({self._bufnr}))") == "run"

    @property
    def pid(self) -> int:
        if not self.alive: return -1
        try:
            # Extract process ID from job_info
            info = vim.eval(f"job_info(term_getjob({self._bufnr}))")
            return int(info.get("process", -1))
        except Exception:
            return -1

    @property
    def children_pids(self) -> list[int]:
        p = self.pid
        return find_children_pids(p) if p > 0 else []

    @property
    def job_id(self) -> JobID | None:
        return str(self._bufnr) if self._bufnr > 0 else None

    @property
    def name(self) -> str:
        return self._request.name

    @property
    def cwd(self) -> Path:
        cwd_val = self._spawn_option.cwd or Path.cwd()
        return Path(cwd_val)

    @property
    def events(self) -> JobEvents:
        return self._core.events