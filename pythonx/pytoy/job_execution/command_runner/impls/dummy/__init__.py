from __future__ import annotations

import queue
import subprocess
import threading
from pathlib import Path
from typing import Any

from pytoy.job_execution.command_runner.impls.core import OutputJobCore
from pytoy.job_execution.command_runner.models import (
    JobEvents,
    JobID,
    OutputJobRequest,
    Snapshot,
    SpawnOption,
)
from pytoy.job_execution.command_runner.protocol import OutputJobProtocol
from pytoy.job_execution.process_utils import find_children_pids
from pytoy.shared.timertask import TimerTask


class OutputJobDummy(OutputJobProtocol):
    def __init__(self, job_request: OutputJobRequest, spawn_option: SpawnOption):
        self._name = job_request.name
        self._core = OutputJobCore(self._name)
        self._job_id = f"dummy-{id(self)}"
        self._alive = True
        self._cwd = Path(spawn_option.cwd or Path().cwd())
        self._proc = subprocess.Popen(
            job_request.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self._cwd,
        )
        self._lock = threading.Lock()
        self._notification_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        threading.Thread(target=self._wait, daemon=True).start()
        self._start_notification_dispatch()

    def _start_notification_dispatch(self) -> None:
        """Dispatch worker-thread notifications to main thread via TimerTask.

        Fulfills the main-thread event contract: all JobEvents must be emitted
        from the main thread (see README.md Design section).
        """

        def _dispatch_pending() -> None:
            while True:
                try:
                    event_type, data = self._notification_queue.get_nowait()
                    if event_type == "stdout":
                        self._core.emit_stdout(data)
                    elif event_type == "stderr":
                        self._core.emit_stderr(data)
                    elif event_type == "exit":
                        self._core.emit_exit(self, data)
                except queue.Empty:
                    break

        TimerTask.register(_dispatch_pending, interval=10)

    def _read_stdout(self) -> None:
        assert self._proc.stdout
        for line in self._proc.stdout:
            self._notification_queue.put(("stdout", line.rstrip("\n")))

    def _read_stderr(self) -> None:
        assert self._proc.stderr
        for line in self._proc.stderr:
            self._notification_queue.put(("stderr", line.rstrip("\n")))

    def _wait(self) -> None:
        code = self._proc.wait()
        self._notification_queue.put(("exit", code))
        self._finalize(code)

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
            self._proc.terminate()
        except Exception:
            pass

    def dispose(self):
        self.terminate()
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass  # ここは割り切る
        self._core.dispose()

    @property
    def snapshot(self) -> Snapshot:
        return self._core.snapshot

    @property
    def pid(self) -> int:
        return self._proc.pid

    @property
    def children_pids(self) -> list[int]:
        return find_children_pids(self.pid) if self._alive else []

    @property
    def events(self) -> JobEvents:
        return self._core.events

    def _finalize(self, code: int) -> None:
        """Mark job as no longer alive (called from worker thread via Queue)."""
        with self._lock:
            if not self._alive:
                return
            self._alive = False
