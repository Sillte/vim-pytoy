from __future__ import annotations
from pytoy.job_execution.command_runner.models import (
    OutputJobRequest,
    SpawnOption,
    JobID,
    JobEvents,
    Snapshot,
    OutputJobProtocol,
)
from pytoy.job_execution.command_runner.impls.core import OutputJobCore
from pathlib import Path
import threading
import subprocess
from pytoy.job_execution.process_utils import find_children_pids


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

        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        threading.Thread(target=self._wait, daemon=True).start()

    def _read_stdout(self):
        assert self._proc.stdout
        for line in self._proc.stdout:
            self._core.emit_stdout(line.rstrip("\n"))

    def _read_stderr(self):
        assert self._proc.stderr
        for line in self._proc.stderr:
            self._core.emit_stderr(line.rstrip("\n"))

    def _wait(self):
        code = self._proc.wait()
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

    def _finalize(self, code):
        with self._lock:
            if not self._alive:
                return
            self._alive = False
        self._core.emit_exit(self, code)
