from __future__ import annotations

import queue
import subprocess
import threading
from pathlib import Path
from typing import Any

from pytoy.shared.timertask import TimerTask
from pytoy.tool_execution.command.infra.contract import JobEvents, JobID, OutputJobProtocol
from pytoy.tool_execution.command.infra.impls.core import OutputJobCore
from pytoy.tool_execution.command.infra.models import OutputJobRequest, Snapshot, SpawnOption
from pytoy.tool_execution.command.infra.process import find_children_pids


class OutputJobDummy(OutputJobProtocol):
    def __init__(self, job_request: OutputJobRequest, spawn_option: SpawnOption):
        self._name = job_request.name
        self._core = OutputJobCore(self._name)
        self._job_id = f"dummy-{id(self)}"
        self._alive = False
        self._cwd = Path(spawn_option.cwd or Path().cwd())
        self._env = spawn_option.env
        self._command = job_request.command
        self._proc: None | subprocess.Popen = None
        self._notification_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._notification_task_name: str | None = None

    def _start_notification_dispatch(self) -> None:
        """Dispatch worker-thread notifications through the TimerTask context."""

        def _dispatch_pending() -> None:
            while True:
                try:
                    event_type, data = self._notification_queue.get_nowait()
                    if event_type == "stdout":
                        self._core.emit_stdout(data)
                    elif event_type == "stderr":
                        self._core.emit_stderr(data)
                    elif event_type == "exit":
                        self._alive = False
                        try:
                            self._core.emit_exit(self, data)
                        finally:
                            self._stop_notification_dispatch()
                except queue.Empty:
                    break

        self._notification_task_name = TimerTask.register(_dispatch_pending, interval=10)

    def _stop_notification_dispatch(self) -> None:
        if self._notification_task_name is None:
            return
        TimerTask.deregister(self._notification_task_name)
        self._notification_task_name = None

    def _read_stdout(self) -> None:
        assert self.proc.stdout
        for line in self.proc.stdout:
            self._notification_queue.put(("stdout", line.rstrip("\n")))

    def _read_stderr(self) -> None:
        assert self.proc.stderr
        for line in self.proc.stderr:
            self._notification_queue.put(("stderr", line.rstrip("\n")))

    def _wait(self) -> None:
        code = self.proc.wait()
        self._notification_queue.put(("exit", code))

    @property
    def proc(self) -> subprocess.Popen:
        if self._proc is None:
            raise RuntimeError("`proc` is not available before `start()`.")
        return self._proc

    def start(self) -> None:
        if self._proc is not None:
            raise RuntimeError("OutputJob has already been started.")
        self._proc = subprocess.Popen(
            self._command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self._cwd,
            env=self._env,
        )
        self._alive = True
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        threading.Thread(target=self._wait, daemon=True).start()
        self._start_notification_dispatch()

    @property
    def job_id(self) -> JobID | None:
        return self._job_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def cwd(self) -> Path:
        return self._cwd

    @property
    def alive(self) -> bool:
        return self._alive

    def terminate(self) -> None:
        try:
            self.proc.terminate()
        except Exception:
            pass

    def dispose(self):
        self._stop_notification_dispatch()
        if self._proc is not None:
            self.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                try:
                    self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass  # ここは割り切る
        self._core.dispose()

    @property
    def snapshot(self) -> Snapshot:
        return self._core.snapshot

    @property
    def pid(self) -> int:
        return self.proc.pid

    @property
    def children_pids(self) -> list[int]:
        return find_children_pids(self.pid) if self._alive else []

    @property
    def events(self) -> JobEvents:
        return self._core.events
