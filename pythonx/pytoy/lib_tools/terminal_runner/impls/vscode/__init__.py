from __future__ import annotations

import codecs
import vim
from pathlib import Path
from pytoy.lib_tools.terminal_runner.impls.vscode.pty_console import PtyConsole
import base64 


import time
from pathlib import Path
from queue import Queue, Empty
from threading import Thread
from typing import Any, Sequence, Callable

from pyte import Screen, Stream
from pytoy.lib_tools.terminal_runner.models import (
    TerminalJobProtocol,
    TerminalJobRequest,
    TerminalDriverProtocol,
    SpawnOption,
    ConsoleSnapshot,
    Snapshot,
    WaitOperation,
    RawStr, 
    LineStr, 
    InputOperation,
    JobEvents,
    JobID
)
from pytoy.lib_tools.terminal_runner.impls.core import TerminalJobCore
from pytoy.infra.core.models import CursorPosition
from pytoy.infra.vim_function import PytoyVimFunctions
from pytoy.infra.events import EventEmitter
from pytoy.lib_tools.process_utils import find_children_pids
from pytoy.lib_tools.terminal_runner.impls.utils import send_ctrl_c

from .virtual_tty import VirtualTTY

from pytoy.infra.timertask import TimerTask

class TerminalJobVSCode(TerminalJobProtocol):
    

    def _on_update(self):
        self._core.update_emitter.fire(self.pid)

    def _on_exit(self):
        def _inner():
            self._core.exit_emitter.fire(0)
            self.dispose()
        TimerTask.execute_oneshot(lambda : _inner(), interval=0)

    def _schedule_update(self):
        if self._update_scheduled:
            return

        self._update_scheduled = True

        def _fire():
            self._update_scheduled = False
            self._core.update_emitter.fire(self.pid)

        # ★ ここが重要
        if hasattr(vim, "session"):
            vim.session.threadsafe_call(_fire)
        else:
            TimerTask.execute_oneshot(lambda: _fire())
        

    def __init__(self, request: TerminalJobRequest, spawn_option: SpawnOption | None = None):
        self._request = request
        self._spawn_option = spawn_option or SpawnOption()
        self._driver = request.driver
        self._update_scheduled = False

        self._core = TerminalJobCore(self._request, self._spawn_option)   

        # 1. Setup Callbacks
        cmd = self._driver.command
        cwd = self._spawn_option.cwd
        env = self._spawn_option.env
        cols = self._request.console.cols or 80
        lines = self._request.console.lines or 96
        self._cwd = cwd
        
        self._on_out_name = PytoyVimFunctions.register(self._on_update, prefix="CommonTTYOut")
        self._on_exit_name = PytoyVimFunctions.register(self._on_exit,  prefix="CommonTTYExit")

        self._tty = VirtualTTY(cmd, cwd=cwd, env=env, lines=lines, cols=cols, on_output=self._schedule_update)

    def _inner(self):
        vim.session.threadsafe_call(lambda: vim.call(self._on_out_name))

    def send(self, input: str) -> None:
        def _send_thread():
            try:
                ops = self._driver.make_operations(input)
                enter_eol = self._driver.eol or TerminalJobCore.get_default_eol()
                
                # snapshot_getter は pyte (メモリ) を見るだけなのでスレッドから呼んでも安全
                snapshot_getter = lambda: self.snapshot
                for op in ops:
                    payload = TerminalJobCore.deal_operation(op, enter_eol, snapshot_getter)
                    if payload:
                        self._tty.send(payload)
            except Exception:
                pass

        # send 専用のスレッドを開始
        Thread(target=_send_thread, daemon=True).start()

    def interrupt(self) -> None:
        self._tty.interrupt()

    def terminate(self) -> None:
        self._tty.terminate()

    def dispose(self) -> None:
        self.terminate()
        # Cleanup input thread
        self._core.dispose()


    @property
    def snapshot(self) -> Snapshot:
        return self._tty.snapshot

    @property
    def job_id(self) -> JobID:
        return self.pid

    @property
    def name(self) -> str:
        return self._request.name

    @property
    def cwd(self) -> Path:
        return Path(self._spawn_option.cwd or Path.cwd())

    @property
    def events(self) -> JobEvents:
        return self._core.events

    @property
    def alive(self) -> bool:
        return self._tty.alive

    @property
    def pid(self) -> int:
        pid =  self._tty.pid
        if pid is None:
            pid = -1
        return pid

    @property
    def children_pids(self) -> list[int]:
        p = self.pid
        return find_children_pids(p) if p > 0 else []





#class TerminalJobVSCodeOld(TerminalJobProtocol):
#    def __init__(self, request: TerminalJobRequest, spawn_option: SpawnOption | None = None):
#        self._request = request
#        self._spawn_option = spawn_option or SpawnOption()
#        self._driver = request.driver
#
#        cols = self._request.console.cols or 80
#        rows = self._request.console.lines or 96
#
#        self._screen = Screen(cols, rows)
#        self._stream = Stream(self._screen)
#        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
#
#        self._core = TerminalJobCore(self._request, self._spawn_option)   
#
#        self._start()
#
#    def _start(self) -> None:
#        # 1. Setup Callbacks
#        cmd = self._driver.command
#        cwd = self._spawn_option.cwd
#        env = self._spawn_option.env
#        size = (self._screen.columns, self._screen.lines)
#
#        self._pty = PtyConsole(cmd, cwd, size, env)
#        self._on_out_name = PytoyVimFunctions.register(self._on_decode_and_emit, prefix="CommonTTYOut")
#        self._on_exit_name = PytoyVimFunctions.register(self._on_vim_exit, prefix="CommonTTYExit")
#
#        def _exe_vim_func(func_name: str, b64_payload: str) -> None:
#            """ スレッドからVimのメインループへ安全に関数実行をスケジュールする。
#            timer_start(0, ...) を使うことで、Vim/Neovim両方で共通のロジックで動作する。
#            """
#            # Neovim (pynvim) の場合
#            if hasattr(vim, 'session'):
#                try:
#                    # threadsafe_call はスレッドから安全に Vim の操作をスケジュールする
#                    vim.session.threadsafe_call(lambda: vim.call(func_name, b64_payload))
#                    return
#                except Exception:
#                    # チャンネルが既に閉じている場合などのエラーをここで握りつぶす
#                    return
#
#            # 本家 Vim の場合
#            # Pythonスレッドから直接 eval を呼ぶ (本家 Vim はこれでキューに入る)
#            vim_script = f"timer_start(0, {{ -> {func_name}('{b64_payload}') }})"
#            try:
#                vim.eval(vim_script)
#            except Exception:
#                pass
#
#        def _read_loop():
#            while self._pty.alive:
#                try:
#                    data = self._pty.read(4096)
#                    if data:
#                        # 1. データをBase64化（エスケープ問題を完全に回避）
#                        b64_payload = base64.b64encode(data.encode('utf-8', 'replace')).decode('ascii')
#                        _exe_vim_func(self._on_out_name, b64_payload)
#                    else:
#                        time.sleep(0.01)
#                except Exception:
#                    break
#
#            try:
#                # threadsafe_call はスレッドから安全に Vim の操作をスケジュールする
#                vim.session.threadsafe_call(lambda: vim.call(self._on_exit_name))
#            except Exception:
#                pass
#        self._reader_thread = Thread(target=_read_loop, daemon=True)
#        self._reader_thread.start()
#
#    def _on_decode_and_emit(self, b64_data: str):
#        # Base64をデコードして生のバイト列(または文字列)に戻す
#        raw_bytes = base64.b64decode(b64_data)
#        decoded_str = self._decoder.decode(raw_bytes, final=False)
#        #raw_data = base64.b64decode(b64_data).decode('utf-8', 'replace')
#        self._stream.feed(decoded_str)
#        self._core.update_emitter.fire(self.pid)
#
#    def _on_vim_exit(self) -> None:
#        self._core.exit_emitter.fire(0)
#        self.dispose()
#
#
#    def send(self, input: str) -> None:
#        def _send_thread():
#            try:
#                ops = self._driver.make_operations(input)
#                enter_eol = self._driver.eol or TerminalJobCore.get_default_eol()
#                
#                # snapshot_getter は pyte (メモリ) を見るだけなのでスレッドから呼んでも安全
#                snapshot_getter = lambda: self.snapshot
#                for op in ops:
#                    payload = TerminalJobCore.deal_operation(op, enter_eol, snapshot_getter)
#                    if payload and self._pty.alive:
#                        self._pty.write(payload)
#            except Exception:
#                pass
#
#        # send 専用のスレッドを開始
#        Thread(target=_send_thread, daemon=True).start()
#
#    def interrupt(self) -> None:
#        if self._pty.alive:
#            self._pty.send_ctrl_c()
#
#    def terminate(self) -> None:
#        if self._pty.alive:
#            self._pty.terminate()
#
#    def dispose(self) -> None:
#        self.terminate()
#        # Cleanup input thread
#        self._core.dispose()
#
#        from pytoy.infra.timertask import TimerTask
#        def _inner():
#            PytoyVimFunctions.deregister(self._on_out_name)
#            PytoyVimFunctions.deregister(self._on_exit_name)
#        TimerTask.execute_oneshot(_inner, interval=0)
#
#    @property
#    def snapshot(self) -> Snapshot:
#        # pyte.screen.display returns a list of visible lines
#        return self._core.snapshot
#        content = "\n".join(self._screen.display)
#        
#        return Snapshot(
#            timestamp=time.time(),
#            console=ConsoleSnapshot(
#                lines=self._screen.lines,
#                cols=self._screen.columns,
#                content=content
#            ),
#            cursor=CursorPosition(
#                line=self._screen.cursor.y,
#                col=self._screen.cursor.x
#            )
#        )
#
#    @property
#    def alive(self) -> bool:
#        return self._pty.alive
#
#    @property
#    def pid(self) -> int:
#        pid =  self._pty.pid
#        if pid is None:
#            pid = -1
#        return pid
#
#    @property
#    def children_pids(self) -> list[int]:
#        p = self.pid
#        return find_children_pids(p) if p > 0 else []
#
#    @property
#    def job_id(self) -> JobID | None:
#        return self._pty.pid
#
#    @property
#    def name(self) -> str:
#        return self._request.name
#
#    @property
#    def cwd(self) -> Path:
#        return Path(self._spawn_option.cwd or Path.cwd())
#
#    @property
#    def events(self) -> JobEvents:
#        return self._core.events
#