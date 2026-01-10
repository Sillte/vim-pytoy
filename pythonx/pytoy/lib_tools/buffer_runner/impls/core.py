from __future__ import annotations 
import vim
from pytoy.lib_tools.buffer_runner.models import OutputJobRequest, SpawnOption, JobID, JobEvents, Snapshot, OutputJobProtocol
from pytoy.infra.core.models.event import Event, EventEmitter
from pytoy.infra.timertask import TimerTask
from typing import TYPE_CHECKING, Any
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

    def emit_stdout(self, line: str):
        line = line.strip("\r")
        self.stdout_lines.append(line)
        self.stdout_emitter.fire(line)

    def emit_stderr(self, line: str):
        line = line.strip("\r")
        self.stderr_lines.append(line)
        self.stderr_emitter.fire(line)

    def emit_exit(self, job_instance: OutputJobProtocol):
        self.exit_emitter.fire(job_instance)

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