from __future__ import annotations

from pathlib import Path

from pyte import Screen, Stream
from pytoy.lib_tools.terminal_runner.models import (
    TerminalJobProtocol,
    TerminalJobRequest,
    TerminalDriverProtocol,
    SpawnOption,
    ConsoleSnapshot,
    Snapshot,
    WaitOperation,
    WaitUntilOperation,
    RawStr, 
    LineStr,
    InputOperation,
    JobEvents,
    JobID
)
from typing import Any, Callable
from pytoy.infra.core.models import CursorPosition
from pytoy.infra.vim_function import PytoyVimFunctions
from pytoy.infra.events import EventEmitter
from pytoy.lib_tools.process_utils import find_children_pids


class TerminalJobCore:
    """
    ターミナルジョブの核となる共通ロジックと状態を管理。
    Vim/Neovimの実装クラスから委譲されて動作する。
    """
    def __init__(self, request: TerminalJobRequest, spawn_option: SpawnOption):
        self.request = request
        self.spawn_option = spawn_option
        self.update_emitter = EventEmitter[int]()
        self.exit_emitter = EventEmitter[Any]()
        
        # 外部に公開するイベントインターフェース
        self._events = JobEvents(
            on_update=self.update_emitter.event,
            on_job_exit=self.exit_emitter.event
        )
        self._cwd = Path(self.spawn_option.cwd or Path.cwd())
        
    @property
    def cwd(self) -> Path:
        return self._cwd

    def get_children_pids(self, parent_pid: int) -> list[int]:
        return find_children_pids(parent_pid) if parent_pid > 0 else []

    def dispose(self):
        self.update_emitter.dispose()
        self.exit_emitter.dispose()
        
    @staticmethod
    def get_default_eol() -> str:
        import os 
        return  "\r\n" if os.name == "nt" else "\n"
    
    @property
    def events(self) -> JobEvents:
        return self._events
    
    @staticmethod
    def deal_operation(op: InputOperation, enter_eol: str, snapshot_getter:Callable[[], Snapshot]) -> str | None:
        """This function is allowed if non-main method called this.
        Return str is expected to send to the backend.
        """
        import time 
        if isinstance(op, RawStr):
            # Protocol: Send the str as is.
            payload = op
        elif isinstance(op, LineStr) or isinstance(op, str):
            # Protocol: Append the appropriate `CR`.  
            # Fallback of `LineStr`, however, `LineStr` is more preferrable.
            # Protocol: Append the appropriate `CR`.  
            payload = op.rstrip("\r\n") + enter_eol
        elif isinstance(op, WaitOperation):
            payload = None
            time.sleep(op.time)
        elif isinstance(op, WaitUntilOperation):
            payload = None
            op.wait_until(snapshot_getter)
        else:
            raise RuntimeError("Implementation Error of driver.")
        return payload
    
    @staticmethod
    def kill_processes(pids: list[int]) -> None:
        from pytoy.lib_tools.process_utils import force_kill
        for child in pids:
            force_kill(child)