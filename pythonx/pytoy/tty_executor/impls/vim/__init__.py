import vim
import time
import json
from pathlib import Path
from typing import Mapping, Any, Self

from pytoy.tty_executor.models import (
    ConsoleConfigration, 
    ConsoleConfigurationRequest, 
    ConsoleSnapshot, 
    WaitOperation,
    SpawnOption,
    InputOperation,
    ExecutorEvents, 
    CursorPosition,
)
from pytoy.tty_executor.protocol import TTYApplicationProtocol, TTYApplicationExecutorProtocol
from pytoy.infra.vim_function import VimFunctionName, PytoyVimFunctions
from pytoy.infra.events import EventEmitter, Event
from pytoy.tty_executor.impls.process_utils import find_children_pids

class VimTTYExecutor(TTYApplicationExecutorProtocol):
    def __init__(self, app: TTYApplicationProtocol,
                 config_request: ConsoleConfigurationRequest | None = None,
                 spawn_option: SpawnOption | None = None):
        self._app = app
        self._config_request = config_request or ConsoleConfigurationRequest()
        self._spawn_option = spawn_option or SpawnOption()
        self._bufnr = -1
        
        # イベント系の初期化
        self._update_emitter = EventEmitter()
        self._jobexit_emitter = EventEmitter[int]()
        self._events = ExecutorEvents(
            on_update=self._update_emitter.event,
            on_job_exit=self._jobexit_emitter.event
        )
        
        self._start()

    def _start(self):
        # 1. 終了および出力コールバックの登録
        self._on_exit_name = PytoyVimFunctions.register(self._on_vim_exit, prefix="VimTTYExit")
        # 出力が届くたびに通知するためのコールバック
        self._on_output_name = PytoyVimFunctions.register(self._on_vim_output, prefix="VimTTYOut")

        # 2. term_start のオプション構築
        options = {
            "hidden": 1,
            "term_cols": self._config_request.width or 80,
            "term_rows": self._config_request.height or 24,
            "out_cb": self._on_output_name,  # 出力があるたびに通知
            "err_cb": self._on_output_name,  # エラー出力も同様
            "exit_cb": self._on_exit_name,
            "norestore": 1,
        }

        if self._spawn_option.cwd:
            options["cwd"] = str(Path(self._spawn_option.cwd).absolute().as_posix())
        if self._spawn_option.env:
            options["env"] = self._spawn_option.env

        # 3. ターミナルの起動
        cmd = self._app.command
        self._bufnr = int(vim.eval(f"term_start({json.dumps(cmd)}, {json.dumps(options)})"))
        
        if self._bufnr <= 0:
            raise RuntimeError(f"Vim term_start failed. buf: {self._bufnr}")
    def _on_vim_output(self, channel, data):
        self._update_emitter.fire(None)

    def notify_update(self):
        """autocmd (TextChanged) 等から呼ばれるフック"""
        self._update_emitter.fire(None)

    def _on_vim_exit(self, job, exit_status):
        # 終了時は即座にイベントを発火
        self._jobexit_emitter.fire(exit_status)
        self.dispose()

    def send(self, input: str | WaitOperation):
        if not self.alive:
            return

        if isinstance(input, str):
            ops = self.app.make_lines(input)
        else:
            ops = [input]
            
        for op in ops: 
            if isinstance(op, str):
                # term_sendkeys は Vim 側の入力キューに積むため非同期的に安全
                vim.command(f"call term_sendkeys({self._bufnr}, {json.dumps(op + "\r")})")
            else:
                time.sleep(op.time)

    def resize(self, width: int, height: int):
        if self._bufnr > 0:
            vim.command(f"call term_setsize({self._bufnr}, {height}, {width})")

    def terminate(self):
        if self.alive:
            vim.command(f"call job_stop(term_getjob({self._bufnr}))")
        self.dispose()

    def dispose(self):
        if self._bufnr > 0:
            vim.command(f"unlet! b:current_executor") # 安全のため
            vim.command(f"bdelete! {self._bufnr}")
            self._bufnr = -1
        PytoyVimFunctions.deregister(self._on_exit_name)
        PytoyVimFunctions.deregister(self._on_output_name)

    @property
    def snapshot(self) -> ConsoleSnapshot:
        """pyte を使わず、Vim ターミナルのバッファから直接スナップショットを作成"""
        import time
        if self._bufnr <= 0:
            return ConsoleSnapshot(timestamp=time.time(),
                                   content="", cursor=CursorPosition(line=0, col=0), 
                                   config=self.console_configuration)

        # 1. 表示されている文字列を取得 (getbufline は 1-indexed)
        # ターミナルバッファの内容をそのままリストで取得
        lines = vim.buffers[self._bufnr][:]

        # 2. カーソル情報の取得 (term_getcursor は [row, col] を返す)
        cursor = vim.eval(f"term_getcursor({self._bufnr})")
        
        return ConsoleSnapshot(
            timestamp=time.time(), 
            content="\n".join(lines),
            cursor=CursorPosition(line=int(cursor[0]) - 1, col=int(cursor[1]) - 1), 
            config=self.console_configuration,
        )

    @property
    def console_configuration(self) -> ConsoleConfigration:
        # 現在のバッファサイズを Vim 側から取得
        width = int(vim.eval(f"getbufvar({self._bufnr}, '&columns')"))
        height = int(vim.eval(f"getbufvar({self._bufnr}, '&lines')"))
        # もし上記で取れない場合は term_getsize を使用
        size = vim.eval(f"term_getsize({self._bufnr})") # [rows, cols]
        return ConsoleConfigration(width=int(size[1]), height=int(size[0]))

    @property
    def pid(self) -> int:
        if self.alive:
            try:
                return int(vim.eval(f"job_info(term_getjob({self._bufnr})).process"))
            except Exception:
                pass
        return -1

    @property
    def alive(self) -> bool:
        if self._bufnr <= 0:
            return False
        return vim.eval(f"job_status(term_getjob({self._bufnr}))") == "run"

    @property
    def busy(self) -> bool | None:
        return self._app.is_busy(self.children_pids, self.snapshot)

    @property
    def app(self) -> TTYApplicationProtocol:
        return self._app

    @property
    def children_pids(self) -> list[int]:
        p = self.pid
        return find_children_pids(p) if p > 0 else []

    def interrupt(self) -> None:
        self._app.interrupt(self.pid, self.children_pids)

    @property
    def events(self) -> ExecutorEvents:
        return self._events
