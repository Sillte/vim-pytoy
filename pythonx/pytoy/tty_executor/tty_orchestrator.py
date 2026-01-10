from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Self, Sequence
from pytoy.ui.pytoy_buffer import PytoyBuffer, BufferID
from pytoy.tty_executor.protocol import TTYApplicationExecutorProtocol, TTYApplicationProtocol
from pytoy.tty_executor.models import SpawnOption
from pytoy.ui.ui_enum import get_ui_enum, UIEnum

class TTYExecutorProvider:
    
    @classmethod
    def make_executor(cls, app: TTYApplicationProtocol, spawn_option: SpawnOption | None = None) -> TTYApplicationExecutorProtocol:
        if get_ui_enum() == UIEnum.VIM:
            from pytoy.tty_executor.impls.vim import VimTTYExecutor
            return VimTTYExecutor(app, spawn_option=spawn_option)
        else:
            from pytoy.tty_executor.impls.nvim import NeovimTTYExecutor
            return NeovimTTYExecutor(app, spawn_option=spawn_option) 


@dataclass
class ExecutionSpec:
    """Specification of execution.

    Note that this specification is not perfect,  
    since it may the current directory changes in the process.
    NOTE: As a specification, `TTYApplicationExecutor` do not catch the change of `cwd`.
    """
    command: str
    env: Mapping[str, Any] | None = None
    start_cwd: str | Path | None = None

    @classmethod
    def from_arguments(cls, app: TTYApplicationProtocol, spawn_option: SpawnOption | None = None) -> Self:
        spawn_option = spawn_option if spawn_option else SpawnOption()
        return cls(command=app.command, env=spawn_option.env, start_cwd=spawn_option.cwd)
        

class TTYOrachestrator:
    def __init__(self,  buffer: PytoyBuffer, app: TTYApplicationProtocol) -> None:
        self._buffer = buffer 
        self._create_executor(app, spawn_option=None)
        self._should_sync = True 
        # on_wiped is a special event since it is related to creation / deletion.

    def _create_executor(self, app: TTYApplicationProtocol, spawn_option: SpawnOption | None = None) -> None:
        self._executor = TTYExecutorProvider.make_executor(app, spawn_option) 
        self._execution_spec = ExecutionSpec.from_arguments(app, spawn_option)
        disposables = []
        events = self.executor.events
        disposables.append(events.on_update.subscribe(self._listen_update))
        self._executor_disposables = disposables
        
    def _dispose_executor(self) -> None:
        for disposable in self._executor_disposables:
            disposable.dispose()
        self.executor.terminate()
        self._executor_disposables = []
        self._execution_spec = None

    def terminate(self) -> None:
        return self._dispose_executor()
        
    def change_application(self, app: TTYApplicationProtocol, spawn_option: SpawnOption | None = None) -> None:
        self._dispose_executor()
        self._create_executor(app, spawn_option=spawn_option)

    def send(self, input: str) -> None:
        self.executor.send(input)

    @property
    def alive(self) -> bool:
        return self.executor.alive

    def interrupt(self, pid: int, children_pids: Sequence[int]) -> None:
        return self.executor.interrupt()


    def _listen_update(self, job_id: int) -> None:
        if self._should_sync:
            snapshot = self._executor.snapshot
            cr = self.buffer.range_operator.entire_character_range
            self.buffer.replace_text(cr, snapshot.content)
            if (window := self.buffer.window):
                window.move_cursor(snapshot.cursor)
        else:
            print("No synchrorinzation.")

    @property
    def buffer(self) -> PytoyBuffer:
        return self._buffer

    @property
    def executor(self) -> TTYApplicationExecutorProtocol:
        return self._executor

    def execeution_spec(self) -> ExecutionSpec | None:
        return self._execution_spec



class TTYOrachestratorManager:
    def __init__(self) -> None:
        self._instances: dict[BufferID, TTYOrachestrator] = dict()
        

    def get(self, buffer: PytoyBuffer) -> TTYOrachestrator | None:
        return self._instances.get(buffer.buffer_id)
        
    def get_or_create(self,
                       buffer: PytoyBuffer,
                       app: TTYApplicationProtocol, 
                       spawn_option: SpawnOption | None = None) -> TTYOrachestrator:
        buffer_id = buffer.buffer_id 
        if buffer_id in self._instances:
            orchestrator =  self._instances[buffer_id]
            query_execution_spec = ExecutionSpec.from_arguments(app, spawn_option)
            if (orchestrator.execeution_spec == query_execution_spec
                and orchestrator.alive):
                return orchestrator
            else:
                orchestrator.change_application(app, spawn_option)
                return orchestrator
        else:
            orchestrator = TTYOrachestrator(buffer, app)
            self._instances[buffer_id] = orchestrator
            buffer.on_wiped.subscribe(self._dispose)
            return orchestrator
    def _dispose(self, buffer_id: BufferID):
        self._instances.pop(buffer_id)
    

    
# Simple Tests.
from pytoy.ui.pytoy_window.facade import PytoyWindowProvider
from pytoy.tty_executor.applications import ShellApplication
from pytoy.infra.timertask import TimerTask
app = ShellApplication("cmd.exe")
window = PytoyWindowProvider().open_window("MOCK", "vertical")
orachestrator = TTYOrachestrator(window.buffer, app)

TimerTask.execute_oneshot(lambda :orachestrator.send("echo hello"), interval=500)
TimerTask.execute_oneshot(lambda :orachestrator.send("echo hell"), interval=1200)
TimerTask.execute_oneshot(lambda :orachestrator.send("echo hel"), interval=1500)
TimerTask.execute_oneshot(lambda :orachestrator.send("echo hel"), interval=2000)


      
