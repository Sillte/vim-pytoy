from __future__ import annotations 
import vim
from pytoy.lib_tools.command_runner.models import OutputJobRequest, SpawnOption, JobID, JobEvents, Snapshot, OutputJobProtocol, JobResult
from pytoy.infra.core.models.event import Event, EventEmitter
from pytoy.infra.timertask import TimerTask
from typing import TYPE_CHECKING, Any, Sequence
from pathlib import Path

import time


class OutputJobCore:
    def __init__(self, name: str):
        self.name = name
        self.stdout_emitter = EventEmitter()
        self.stderr_emitter = EventEmitter()
        self.exit_emitter = EventEmitter()
        
        self.stdout_lines: list[str] = []
        self.stderr_lines: list[str] = []
        self.disposables: list[Any] = [] # 共通のリスナー解除用

    def emit_stdout(self, line: str) -> None:
        line = line.strip("\r")
        self.stdout_lines.append(line)
        self.stdout_emitter.fire(line)

    def emit_stderr(self, line: str) -> None:
        line = line.strip("\r")
        self.stderr_lines.append(line)
        self.stderr_emitter.fire(line)

    def emit_exit(self, job_instance: OutputJobProtocol, status_code: int) -> None:
        result = JobResult(job_id=job_instance.job_id,
                           status=status_code,
                           snapshot=self.snapshot)

        self.exit_emitter.fire(result)
        
    def normalize_command(self, command: str | list[str] | tuple[str]) -> list[str]:
        from shlex import split as shlex_split
        if isinstance(command, str):
            import platform
            is_windows = platform.system() == "Windows"
            command = list(shlex_split(command, posix=not is_windows))
        return list(command)

    @property
    def snapshot(self) -> Snapshot:
        return Snapshot(
            stdout="\n".join(self.stdout_lines),
            stderr="\n".join(self.stderr_lines),
            name=self.name,
            timestamp=time.time()
        )

    @property
    def events(self) -> JobEvents:
        return JobEvents(
            on_job_exit=self.exit_emitter.event,
            on_update_stdout_line=self.stdout_emitter.event,
            on_update_stderr_line=self.stderr_emitter.event
        )
        

    def dispose(self):
        for d in self.disposables:
            d.dispose()
        self.disposables.clear()
        self.stdout_emitter.dispose()
        self.stderr_emitter.dispose()
        self.exit_emitter.dispose()