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
import json

class VimTTYExecutor(TTYApplicationExecutorProtocol):
    def __init__(self, app: TTYApplicationProtocol,
                 config_request: ConsoleConfigurationRequest | None = None,
                 spawn_option: SpawnOption | None = None):
        self._app = app
        self._config_request = config_request or ConsoleConfigurationRequest()
        self._spawn_option = spawn_option or SpawnOption()
        self._bufnr = -1
        self._job = None
        self._chan = None
        self._screen = Screen(
            self._config_request.width or 80, 
            self._config_request.height or 24
        )

        self._stream = Stream(self._screen)

        self._update_emitter = EventEmitter()
        self._jobexit_emitter = EventEmitter[int]()
        
        # 識別用のユニークキー
        self._events = ExecutorEvents(on_update=self._update_emitter.event,
                                     on_job_exit=self._jobexit_emitter.event) # EventEmitter 等をまとめたクラス
        self._start()

    def _start(self):
        # 1. コールバックの登録 (Vim側から呼ばれる関数名)
        # ターミナルの出力を pyte に流し込むためのフック
        self._on_output_name = PytoyVimFunctions.register(self._on_vim_output, prefix="VimTTYOut")
        self._on_exit_name = PytoyVimFunctions.register(self._on_vim_exit, prefix="VimTTYExit")

        # 2. term_start のオプション構築
        # 'hidden': 1 でバッファを画面に出さずにバックグラウンドで動かす
        options = {
            "hidden": 1,
            "term_cols": self._config_request.width or 80,
            "term_rows": self._config_request.height or 24,
            "out_cb": self._on_output_name,
            "err_cb": self._on_output_name,
            "exit_cb": self._on_exit_name,
            "mode": "raw",
            "norestore": 1, # セッション保存対象外
        }

        if self._spawn_option.cwd:
            options["cwd"] = str(Path(self._spawn_option.cwd).absolute().as_posix())
        if self._spawn_option.env:
            options["env"] = self._spawn_option.env

        # 3. ターミナルの起動
        # cmd は String または List[String]
        cmd = self._app.command
        cmd_str = json.dumps(cmd)
        opt_str = json.dumps(options)
        
        # term_start はバッファ番号を返す
        self._bufnr = int(vim.eval(f"term_start({cmd_str}, {opt_str})"))
        
        if self._bufnr <= 0:
            raise RuntimeError(f"Vim term_start failed. buf: {self._bufnr}")

        # 4. Job と Channel の取得 (制御用)
        self._job = vim.eval(f"term_getjob({self._bufnr})")
        
    def _on_vim_output(self, channel, data):
        """Vimのout_cbから呼ばれる。dataはstr"""
        self._stream.feed(data)
        self._update_emitter.fire(None)

    def _on_vim_exit(self, job, exit_status):
        self.dispose()
        self._jobexit_emitter.fire(self._bufnr)

    def send(self, input: str | WaitOperation):
        """入力の送信"""
        # term_sendkeys を使うと、特殊キーの扱いも Vim に任せられる
        # rawデータを送る場合は ch_sendraw でも良いが、term_sendkeys がより確実
        if isinstance(input, str):
            ops = self.app.make_lines(input)
        else:
            ops = [input]
        for op in ops: 
            if isinstance(op, str):
                data_json = json.dumps(op)
                vim.command(f"call term_sendkeys({self._bufnr}, {data_json})")
            else:
                time.sleep(op.time)

    def resize(self, width: int, height: int):
        """リサイズ (Vim 9.1 ならこれが一番確実)"""
        vim.command(f"call term_setsize({self._bufnr}, {height}, {width})")

    def terminate(self):
        """プロセスの強制終了"""
        if self._bufnr > 0:
            vim.command(f"call job_stop(term_getjob({self._bufnr}))")
            self.dispose()

    def dispose(self):
        """後処理: 変数解除やバッファ削除"""
        if self._bufnr > 0:
            vim.command(f"bdelete! {self._bufnr}")
            self._bufnr = -1
        PytoyVimFunctions.deregister(self._on_output_name)
        PytoyVimFunctions.deregister(self._on_exit_name)

    @property
    def snapshot(self) -> ConsoleSnapshot:
        # pyte.screen.display は文字列のリストを返す
        ...

    @property
    def console_configuration(self) -> ConsoleConfigration:
        columns = self._screen.columns
        lines = self._screen.lines
        return ConsoleConfigration(width=columns, height=lines)
    
    @property
    def app(self) -> TTYApplicationProtocol:
        return self._app

    @property
    def pid(self) -> int:
        if self._bufnr > 0:
            # 1. ターミナルバッファからジョブオブジェクトを取得し、その情報を eval する
            # job_info().process が PID に相当します
            try:
                # VimScript: job_info(term_getjob(bufnr)).process
                pid_val = vim.eval(f"job_info(term_getjob({self._bufnr})).process")
                return int(pid_val)
            except Exception:
                return -1
        return -1

    @property
    def children_pids(self) -> list[int]:
        return find_children_pids(self.pid)

    def interrupt(self) ->  None:
        self._app.interrupt(self.pid, self.children_pids)

    @property
    def alive(self) -> bool:
        if self._bufnr <= 0:
            return False
        # term_getjob でバッファ紐付けのジョブを取得し、そのステータスを確認
        # ステータスが "run" であれば生存、それ以外（"dead", "fail"）は死亡
        status = vim.eval(f"job_status(term_getjob({self._bufnr}))")
        return status == "run"

    @property
    def busy(self) -> bool | None:
        self._app.is_busy(self.children_pids, self.snapshot)

    @property
    def events(self) -> ExecutorEvents:
        return self._events
