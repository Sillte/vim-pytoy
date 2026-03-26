from __future__ import annotations

from pathlib import Path
from pytoy.job_execution.terminal_runner.impls.utils.pty_console import PtyConsole


from threading import Thread

from pyte import Screen, Stream
from pytoy.job_execution.terminal_runner.models import (
    TerminalJobProtocol,
    TerminalJobRequest,
    SpawnOption,
    Snapshot,
    JobEvents,
    JobID,
)
from pytoy.job_execution.terminal_runner.impls.core import TerminalJobCore
from pytoy.shared.lib.function import FunctionRegistry
from pytoy.job_execution.process_utils import find_children_pids

from pytoy.job_execution.terminal_runner.impls.utils.virtual_tty import VirtualTTY

from pytoy.shared.timertask import TimerTask


class TerminalJobDummy(TerminalJobProtocol):
    def _on_update(self):
        self._core.update_emitter.fire(self.pid)

    def _on_tty_exit(self):
        def _inner():
            self._core.exit_emitter.fire(0)
            self.dispose()

        TimerTask.execute_oneshot(lambda: _inner(), interval=0)

    def _schedule_update(self):
        if self._update_scheduled:
            return

        self._update_scheduled = True

        def _fire():
            self._update_scheduled = False
            self._core.update_emitter.fire(self.pid)

        TimerTask.execute_oneshot(lambda: _fire())

    def __init__(self, request: TerminalJobRequest, spawn_option: SpawnOption | None = None):
        self._request = request
        self._spawn_option = spawn_option or SpawnOption()
        self._driver = request.driver
        self._update_scheduled = False

        self._core = TerminalJobCore(self._request, self._spawn_option)

        # 1. Setup Callbacks
        cmd = self._driver.command
        cwd = self._spawn_option.cwd
        env = self._spawn_option.env
        cols = self._request.console.cols or 80
        lines = self._request.console.lines or 96
        self._cwd = cwd

        self._on_out = FunctionRegistry.register(self._on_update, prefix="CommonTTYOut")

        # Note: Curretly, `self._on_exit` is not used.
        self._on_exit = FunctionRegistry.register(self._on_tty_exit, prefix="CommonTTYExit")

        self._tty = VirtualTTY(cmd, cwd=cwd, env=env, lines=lines, cols=cols, on_output=self._schedule_update)

    def _inner(self):
        self._on_out()

    def send(self, input: str) -> None:
        def _send_thread():
            try:
                ops = self._driver.make_operations(input)
                enter_eol = self._driver.eol or TerminalJobCore.get_default_eol()

                # snapshot_getter は pyte (メモリ) を見るだけなのでスレッドから呼んでも安全
                snapshot_getter = lambda: self.snapshot
                for op in ops:
                    payload = TerminalJobCore.deal_operation(op, enter_eol, snapshot_getter)
                    if payload:
                        self._tty.send(payload)
            except Exception:
                pass

        # send 専用のスレッドを開始
        Thread(target=_send_thread, daemon=True).start()

    def interrupt(self) -> None:
        self._tty.interrupt()

    def terminate(self) -> None:
        self._tty.terminate()

    def dispose(self) -> None:
        self.terminate()
        # Cleanup input thread
        self._core.dispose()

    @property
    def snapshot(self) -> Snapshot:
        return self._tty.snapshot

    @property
    def job_id(self) -> JobID:
        return self.pid

    @property
    def name(self) -> str:
        return self._request.name

    @property
    def cwd(self) -> Path:
        return Path(self._spawn_option.cwd or Path.cwd())

    @property
    def events(self) -> JobEvents:
        return self._core.events

    @property
    def alive(self) -> bool:
        return self._tty.alive

    @property
    def pid(self) -> int:
        pid = self._tty.pid
        if pid is None:
            pid = -1
        return pid

    @property
    def children_pids(self) -> list[int]:
        p = self.pid
        return find_children_pids(p) if p > 0 else []
