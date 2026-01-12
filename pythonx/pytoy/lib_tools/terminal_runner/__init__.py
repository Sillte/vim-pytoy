from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping, Any, TYPE_CHECKING

#from pytoy.lib_tools.buffer_runner.models import OutputJobProtocol, OutputJobRequest, SpawnOption, JobEvents
from pytoy.lib_tools.terminal_runner.models import TerminalJobProtocol, TerminalJobRequest, SpawnOption, JobEvents, Snapshot, JobID
from pytoy.ui.ui_enum import get_ui_enum, UIEnum
from pytoy.ui import PytoyBuffer
from pytoy.ui.pytoy_buffer import make_buffer, make_duo_buffers
if TYPE_CHECKING:
    from pytoy.contexts.pytoy import GlobalPytoyContext


def _solve_buffer(buffer: PytoyBuffer | str):
    if isinstance(buffer, str):
        return make_buffer(buffer)
    return buffer

def make_terminal_job(job_request: TerminalJobRequest, spawn_option: SpawnOption) -> TerminalJobProtocol:
    ui_enum = get_ui_enum()
    if ui_enum == UIEnum.VIM:
        from pytoy.lib_tools.terminal_runner.impls.vim import TerminalJobVim
        return TerminalJobVim(job_request, spawn_option)
    elif ui_enum in {UIEnum.NVIM, UIEnum.VSCODE}:
        from pytoy.lib_tools.terminal_runner.impls.nvim import TerminalJobNvim
        return TerminalJobNvim(job_request, spawn_option)
    else:
        raise RuntimeError(f"Unsupported UI: {ui_enum}")
    

class TerminalJobRunner:
    
    @classmethod
    def solve_buffer(cls, buffer: PytoyBuffer | str) -> PytoyBuffer:
        return _solve_buffer(buffer)

    def __init__(self, 
                 buffer: PytoyBuffer | str,
                 *,
                 init_buffer: bool = True,
                 terminal_job_factory: Callable[..., TerminalJobProtocol] = make_terminal_job,
                 ctx: GlobalPytoyContext | None = None) -> None:
        
        # Terminal behaves on a single buffer
        self._buffer = _solve_buffer(buffer)
        
        if init_buffer:
            self._buffer.init_buffer()
            
        self._terminal_job_factory = terminal_job_factory
        self._terminal_job: TerminalJobProtocol | None = None
        self._job_disposables: list[Any] = []
        
    @property
    def buffer(self) -> PytoyBuffer:
        return self._buffer
    
    @property
    def job_id(self) -> JobID:
        if self._terminal_job:
            return self._terminal_job.job_id
        raise RuntimeError("TerminalJob is not created yet.")

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
        disposables.append(
            job_events.on_job_exit.subscribe(lambda _: self._dispose_job())
        )
        
        if request.on_exit:
            disposables.append(job_events.on_job_exit.subscribe(request.on_exit))
            
        return disposables

    def run(self, 
            request: TerminalJobRequest, 
            spawn_option: SpawnOption | None = None) -> None:
        if self._terminal_job:
            raise RuntimeError("TerminalRunner is already running.")

        spawn_option = spawn_option or SpawnOption()
        
        self._terminal_job = self._terminal_job_factory(request, spawn_option)
        
        self._job_disposables = []
        self._job_disposables += self._wire_events(request, self._terminal_job.events)

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
        if (window := self.buffer.window):
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
            raise ValueError("Terminal Job is not created.")
        return self._terminal_job.events

    def terminate(self) -> None:
        if not self._terminal_job:
            return
        self._terminal_job.terminate()
        
if __name__ == "__main__":
    # Simple Tests.
    from pytoy.ui.pytoy_window.facade import PytoyWindowProvider
    from pytoy.lib_tools.terminal_runner.drivers import ShellDriver
    from pytoy.lib_tools.terminal_runner.drivers import IPythonDriver
    from pytoy.infra.timertask import TimerTask
    #driver = ShellDriver("cmd.exe")

    driver = IPythonDriver()
    window = PytoyWindowProvider().open_window("MOCK", "vertical")

    
    request = TerminalJobRequest(driver=driver, on_exit=lambda _: print("END"))
    runner = TerminalJobRunner(window.buffer)
    runner.run(request)

    TimerTask.execute_oneshot(lambda :runner.send("dir"), interval=500)
    TimerTask.execute_oneshot(lambda :runner.send("echo BAfAFAF"), interval=1200)
    TimerTask.execute_oneshot(lambda : print(runner.snapshot.content), interval=3000)

