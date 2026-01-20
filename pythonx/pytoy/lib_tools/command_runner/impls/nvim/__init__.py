from __future__ import annotations 
import vim
from pytoy.lib_tools.command_runner.models import OutputJobRequest, SpawnOption, JobID, JobEvents, Snapshot, OutputJobProtocol
from pytoy.lib_tools.command_runner.impls.core import OutputJobCore
from pytoy.lib_tools.process_utils import  find_children_pids
from pytoy.infra.core.models.event import Event, EventEmitter
from pytoy.infra.vim_function import PytoyVimFunctions
from pytoy.infra.timertask import TimerTask
from typing import TYPE_CHECKING, Any, Callable
from pathlib import Path

if TYPE_CHECKING:
    from pytoy.contexts.vim import GlobalVimContext

class OutputJobNvim(OutputJobProtocol):
    def __init__(self, job_request: OutputJobRequest, spawn_option: SpawnOption, *, ctx: Any = None):
        self._name = job_request.name
        self._core = OutputJobCore(self._name)
        self._job_id_int: int = -1
        self._start(job_request, spawn_option)

    def _start(self, job_request: OutputJobRequest, spawn_option: SpawnOption):
        # Neovimのコールバック: (job_id, data, event)
        # dataは必ず文字列のリストで届く
        def _on_event(job_id: int, data: list[str], event: str):
            def _emit(func: Callable, data: list[str]): 
                n_lines = len(data)
                for i, line in enumerate(data):
                    if i ==  n_lines -1 and (not line):
                        pass
                    else:
                        func(line)
            if event == 'stdout':
                _emit(self._core.emit_stdout, data)
            elif event == 'stderr':
                _emit(self._core.emit_stderr, data)

            elif event == 'exit':
                # 第2引数の data に終了コード（int）が入る
                exit_code = data if isinstance(data, int) else 0
                self._core.emit_exit(self, exit_code) 

        # イベントハンドラの登録
        on_event_vimfunc = PytoyVimFunctions.register(_on_event, prefix="OutputJobNvim")

        def _cleanup():
            PytoyVimFunctions.deregister(on_event_vimfunc)
            self.dispose()

        # 終了時クリーンアップ
        self._core.disposables.append(
            self.events.on_job_exit.subscribe(lambda _: TimerTask.execute_oneshot(_cleanup, interval=0))
        )

        self._cwd = str(spawn_option.cwd or Path().cwd().absolute())
        # Neovim の jobstart オプション
        option: dict[str, Any] = {
            "on_stdout": on_event_vimfunc,
            "on_stderr": on_event_vimfunc,
            "on_exit": on_event_vimfunc,
            "cwd": self._cwd,
        }
        if spawn_option.env:
            option["env"] = spawn_option.env

        cmd = job_request.command

        # 実行
        try:
            self._job_id_int = vim.call('jobstart', cmd, option)
        except Exception as e:
            raise ValueError(f"Failed to start Neovim job: {e}")

        if self._job_id_int <= 0:
            # 0: invalid arguments, -1: executable not found
            raise ValueError(f"Failed to execute the command, jobstart returned {self._job_id_int}")

    @property
    def alive(self) -> bool:
        try:
            # jobwait に 0ms 指定することで、現在のステータスを非ブロックで取得
            # 返り値が -1 なら「まだ動いている」
            return vim.call('jobwait', [self._job_id_int], 0)[0] == -1
        except Exception:
            return False

    def terminate(self) -> None:
        if self.alive:
            try:
                vim.call('jobstop', self._job_id_int)
            except Exception:
                pass

    def dispose(self) -> None:
        self.terminate()
        self._core.dispose()

    # --- Protocol Implementation (Core 委譲) ---
    @property
    def cwd(self) -> Path:
        return Path(self._cwd)

    @property
    def events(self) -> JobEvents:
        return self._core.events
    @property
    def snapshot(self) -> Snapshot:
        return self._core.snapshot
    @property
    def name(self) -> str:
        return self._name
    @property
    def job_id(self) -> JobID:
        return self._job_id_int
    
    @property
    def pid(self) -> int:
        try:
            return int(vim.call('jobpid', self._job_id_int))
        except Exception:
            return -1
    @property
    def children_pids(self) -> list[int]:
        return find_children_pids(self.pid)
