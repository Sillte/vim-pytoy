import vim
import time
from pathlib import Path
from typing import Mapping, Any, Self
from pyte import Screen, Stream
from pytoy.tty_executor.models import (
    ConsoleConfigration, 
    ConsoleConfigurationRequest, 
    ConsoleSnapshot, 
    WaitOperation,
    SpawnOption,
    InputOperation,
    ExecutorEvents, 
)
from pytoy.tty_executor.protocol import TTYApplicationProtocol, TTYApplicationExecutorProtocol

from pytoy.infra.vim_function import VimFunctionName, PytoyVimFunctions
from pytoy.infra.timertask import TimerTask
from pytoy.infra.events import EventEmitter, Event

from dataclasses import dataclass, field
from queue import Queue, Empty
from threading import Thread
from pytoy.tty_executor.impls.process_utils import force_kill,  find_children_pids


@dataclass
class InputSolverTask: 
    job_id: int
    app: TTYApplicationProtocol
    queue: Queue = field(default_factory=Queue)
    eol = "\r"
    alive: bool = True 

    
    def send(self, inputs: str | WaitOperation) -> None:
        if isinstance(inputs, str):
            ops = self.app.make_lines(inputs)
        else:
            ops = [inputs]

        for op in ops: 
            self.queue.put(op)
        
    def loop(self) -> None:
        while self.alive:
            try:
                op = self.queue.get(timeout=10.0)  # To prevent the infinite loop. 
            except Empty:
                continue
            if op is None:
                self.alive = False
                break # 終了合図
            try:
                if isinstance(op, str):
                    # 各コマンドの末尾に物理改行を付与して送信
                    payload = op + self.eol
                    # NeovimのAPIを別スレッドから呼ぶための安全な方法
                    vim.session.threadsafe_call(
                        vim.call, 'chansend', self.job_id, payload
                    )
                elif isinstance(op, WaitOperation):
                    time.sleep(op.time)
            except Exception as e:
                pass
            finally:
                self.queue.task_done()

@dataclass
class InputSolver: 
    task: InputSolverTask
    thread: Thread

    @classmethod
    def create(cls, job_id: int, app: TTYApplicationProtocol, exit_event: Event[int]) -> Self:
        task = InputSolverTask(job_id=job_id, app=app)
        thread = Thread(target=task.loop, daemon=True)
        thread.start()
        self = cls(task=task, thread=thread)
        exit_event.subscribe(lambda _: self.terminate())
        return self

    def send(self, inputs: str | WaitOperation) -> None:
        self.task.send(inputs)

    
    def terminate(self) -> None:
        self.task.alive = False
        
    @property
    def alive(self):
        return self.task.alive


class NeovimTTYExecutor(TTYApplicationExecutorProtocol):
    def __init__(
        self,
        app: TTYApplicationProtocol,  
        config_request: ConsoleConfigurationRequest | None = None, 
        spawn_option: SpawnOption | None = None,
    ) -> None:
        if config_request is None:
            config_request = ConsoleConfigurationRequest()
        width = config_request.width or 80
        height = config_request.height or 24

        self._screen = Screen(width, height)
        self._stream = Stream(self._screen)
        
        self._update_emitter = EventEmitter()
        

        self._jobexit_emitter = EventEmitter[int]()
        self._events = ExecutorEvents(on_update=self._update_emitter.event,
                                      on_job_exit=self._jobexit_emitter.event)
        self._start(app, spawn_option)

        
    @property
    def events(self) -> ExecutorEvents:
        return self._events

    def _start(self, app: TTYApplicationProtocol, spawn_option: SpawnOption | None = None) -> None:
        self._app: TTYApplicationProtocol  = app
        self._spawn_option = spawn_option if spawn_option else SpawnOption()
        
        option = self._construct_jobstart_option(self._spawn_option)

        self._job_id = vim.call('jobstart', app.command, option)
        if not self._job_id:
            raise RuntimeError("Failed to start the job.")

        self._input_solver = InputSolver.create(self._job_id, self._app, self.events.on_job_exit)
        

    def _construct_jobstart_option(self, spawn_option: SpawnOption) -> dict[str, Any]:
        on_output_vimfunc =  PytoyVimFunctions.register(self._on_output, prefix="TTYApplicationOnOutput")
        on_exit_vimfunc =  PytoyVimFunctions.register(self._on_exit, prefix="TTYApplicatioOnExit")
        def _deregister(*args):
            PytoyVimFunctions.deregister(on_output_vimfunc)
            PytoyVimFunctions.deregister(on_exit_vimfunc)
            disposable.dispose()
        disposable = self.events.on_job_exit.subscribe(_deregister) 

        option = {'pty': True,
        'width': self.console_configuration.width,
        'height': self.console_configuration.height,
        'on_stdout': on_output_vimfunc,
        'on_stderr': on_output_vimfunc, 
        'on_exit': on_exit_vimfunc,
        'stdout_buffered': False}
        if (cwd := spawn_option.cwd):
            option["cwd"] = Path(cwd).absolute().as_posix()
        if (env := spawn_option.env):
            option["env"] = env
        return option

    @property
    def console_configuration(self) -> ConsoleConfigration:
        columns = self._screen.columns
        lines = self._screen.lines
        return ConsoleConfigration(width=columns, height=lines)

    
    def _on_exit(self, job_id: int, exit_code: int, event: str) -> None:
        self._jobexit_emitter.fire(job_id)
        

    def _on_output(self, job_id: int, data: list[str], event: str) -> None:
        """Neovimのコールバック: 受信データをpyteに供給"""
        # NeovimのdataリストをPTYの改行コードで結合
        chunk = "\r\n".join(data)
        self._stream.feed(chunk)
        self._update_emitter.fire(None)


    def send(self, input: str | WaitOperation) -> None:
        self._input_solver.send(input)
        
    @property
    def busy(self) -> bool | None:
        self._app.is_busy(self.children_pids, self.snapshot)

    def interrupt(self) ->  None:
        self._app.interrupt(self.pid, self.children_pids)
            
    @property
    def snapshot(self) -> ConsoleSnapshot:
        # pyte.screen.display は文字列のリストを返す
        content = "\n".join(self._screen.display)
        
        # カーソル位置の変換 (pyte は 0-indexed)
        from pytoy.infra.core.models import CursorPosition
        cursor = CursorPosition(line=self._screen.cursor.y, col=self._screen.cursor.x)
        
        return ConsoleSnapshot(
            timestamp=time.time(), 
            content=content,
            config=self.console_configuration,
            cursor=cursor
        )

    @property
    def pid(self) -> int:
        if self._job_id is not None:
            return vim.call('jobpid', self._job_id)
        return -1

    @property
    def children_pids(self) -> list[int]:
        return find_children_pids(self.pid)
    

    @property
    def alive(self) -> bool:
        if self._job_id is None:
            return False
        # チャンネルが生きていればTrue
        return vim.call('jobwait', [self._job_id], 0)[0] == -1

    def terminate(self) -> None:
        if self._job_id is not None:
            vim.call('jobstop', self._job_id)
            self._jobexit_emitter.fire(self._job_id)
            self._job_id = None
    def __del__(self):
        try:
            self.terminate()
        except:
            pass


