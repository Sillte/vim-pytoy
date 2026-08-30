from pathlib import Path
from typing import Callable

from pytoy.shared.lib.backend import BackendEnum, get_backend_enum
from pytoy.shared.ui import PytoyBuffer
from pytoy.shared.ui.pytoy_buffer import BufferSource, make_buffer
from pytoy.tool_execution.terminal.contract.models import (
    Snapshot,
)
from pytoy.tool_execution.terminal.infra.runner.models import (
    JobEvents,
    JobID,
    SpawnOption,
    TerminalJobProtocol,
    TerminalJobRequest,
)


def make_terminal_job(job_request: TerminalJobRequest, spawn_option: SpawnOption) -> TerminalJobProtocol:
    backend_enum = get_backend_enum()
    if backend_enum == BackendEnum.VIM:
        from pytoy.tool_execution.terminal.infra.runner.impls.vim import TerminalJobVim

        return TerminalJobVim(job_request, spawn_option)
    elif backend_enum == BackendEnum.NVIM:
        from pytoy.tool_execution.terminal.infra.runner.impls.nvim import TerminalJobNvim

        return TerminalJobNvim(job_request, spawn_option)
    elif backend_enum == BackendEnum.VSCODE:
        from pytoy.tool_execution.terminal.infra.runner.impls.vscode import TerminalJobVSCode

        return TerminalJobVSCode(job_request, spawn_option)
    else:
        from pytoy.tool_execution.terminal.infra.runner.impls.dummy import TerminalJobDummy

        return TerminalJobDummy(job_request, spawn_option)


class TerminalJobRunner:
    @classmethod
    def solve_buffer(cls, arg: str | Path | BufferSource | PytoyBuffer) -> PytoyBuffer:
        if isinstance(arg, (str, Path, BufferSource)):
            return make_buffer(BufferSource.from_any(arg))
        else:
            return arg

    def __init__(
        self,
        request: TerminalJobRequest,
        buffer: PytoyBuffer | str,
        spawn_option: SpawnOption | None = None,
        *,
        init_buffer: bool = True,
        terminal_job_factory: Callable[..., TerminalJobProtocol] = make_terminal_job,
    ) -> None:

        # Terminal behaves on a single buffer
        self._buffer = self.solve_buffer(buffer)

        if init_buffer:
            self._buffer.init_buffer()

        self._terminal_job_factory = terminal_job_factory
        self._terminal_job = self._terminal_job_factory(request, spawn_option)
        self._job_disposables = self._wire_events(request=request, job_events=self._terminal_job.events)

    @property
    def buffer(self) -> PytoyBuffer:
        return self._buffer

    @property
    def job_id(self) -> JobID:
        if self._terminal_job:
            return self._terminal_job.job_id
        raise RuntimeError("TerminalJob has disappers already.")

    def _wire_events(self, request: TerminalJobRequest, job_events: JobEvents):
        disposables = []

        # 1. Update event: Triggered when terminal content changes
        # Terminal content is usually managed by the Vim/Nvim terminal buffer itself,
        # but we can hook this to update UI components or sidebars.
        d_upd = job_events.on_update.subscribe(self._on_terminal_update)

        # 2. Sync lifecycle with PytoyBuffer
        buffer_events = self._buffer.events
        d_buf_wiped = buffer_events.on_wiped.subscribe(lambda _: self.dispose())

        disposables += [d_upd, d_buf_wiped]

        # 3. Job Exit logic
        disposables.append(job_events.on_job_exit.subscribe(lambda _: self._dispose_job()))

        return disposables

    def run(self) -> None:
        if self._terminal_job is None:
            raise RuntimeError("Already, job has disappers.")
        self._terminal_job.start()

    def send(self, input_str: str) -> None:
        """Send input to the running terminal driver."""
        if self._terminal_job:
            self._terminal_job.send(input_str)

    def interrupt(self) -> None:
        if self._terminal_job:
            self._terminal_job.interrupt()

    def _on_terminal_update(self, bufnr: int):
        if not self._terminal_job:
            return
        snapshot = self._terminal_job.snapshot
        cr = self.buffer.range_operator.entire_character_range
        self.buffer.replace_text(cr, snapshot.content)
        if window := self.buffer.window:
            window.move_cursor(snapshot.cursor)

        # Here we could perform logic like auto-scrolling
        # or notifying the GlobalContext about state changes.
        pass

    def _dispose_job(self):
        if self._terminal_job:
            self._terminal_job.terminate()
        self._terminal_job = None

        for d in self._job_disposables:
            d.dispose()
        self._job_disposables.clear()

    def dispose(self) -> None:
        self._dispose_job()

    @property
    def alive(self) -> bool:
        return self._terminal_job.alive if self._terminal_job else False

    @property
    def snapshot(self) -> Snapshot | None:
        if self._terminal_job:
            return self._terminal_job.snapshot
        return None

    @property
    def events(self) -> JobEvents:
        if not self._terminal_job:
            raise ValueError("Terminal Job is already dead.")
        return self._terminal_job.events

    def terminate(self) -> None:
        if not self._terminal_job:
            return
        self._terminal_job.terminate()
