from __future__ import annotations

import codecs
import time
from threading import Thread
from pathlib import Path
from typing import Callable, Optional

from pyte import Screen, Stream

from pytoy.lib_tools.terminal_runner.models import Snapshot, ConsoleSnapshot, CursorPosition
from pytoy.infra.core.models import CursorPosition
from pytoy.lib_tools.terminal_runner.impls.vscode.pty_console import PtyConsole, PtyConsoleProtocol


class VirtualTTY:
    """
    VirtualTTY は OS の PTY と pyte を組み合わせた
    仮想端末エンジンであり、UI から完全に独立している。
    """

    def __init__(
        self,
        cmd: str | list[str],
        *,
        cwd: Path | str | None = None,
        env: dict[str, str] | None = None,
        lines: int = 24,
        cols: int = 80,
        on_output: Callable[[], None] | None = None,
        on_exit: Callable[[], None] | None = None,
    ) -> None:
        self._lines: int = lines
        self._cols: int = cols

        self._screen: Screen = Screen(cols, lines)
        self._stream: Stream = Stream(self._screen)
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        
        if isinstance(cwd, Path):
            cwd = cwd.as_posix()

        self._pty: PtyConsoleProtocol = PtyConsole(
            cmd=cmd,
            cwd=cwd,
            size=(lines, cols),
            env=env,
        )

        self._on_output = on_output
        self._on_exit = on_exit

        self._reader_thread: Thread = Thread(
            target=self._read_loop,
            daemon=True,
        )
        self._reader_thread.start()

    # -------------------------
    # PTY interaction
    # -------------------------

    def send(self, text: str) -> None:
        if self._pty.alive:
            self._pty.write(text)

    def send_ctrl_c(self) -> None:
        if self._pty.alive:
            self._pty.send_ctrl_c()

    def resize(self, *, lines: int, cols: int) -> None:
        self._lines = lines
        self._cols = cols
        self._screen.resize(lines, cols)
        self._pty.resize(lines, cols)

    def interrupt(self) -> None:
        if self._pty.alive:
            self._pty.send_ctrl_c()

    def terminate(self) -> None:

        if self._pty.alive:
            self._pty.terminate()

    # -------------------------
    # State
    # -------------------------

    @property
    def alive(self) -> bool:
        return self._pty.alive

    @property
    def pid(self) -> int | None:
        return self._pty.pid

    @property
    def snapshot(self) -> Snapshot:
        # 1. 各行の右空白削除
        # display は pyte の内部状態なので、念のためコピーを取るかリストの内包表記で処理
        display_lines = self._screen.display
        processed_lines = [line.rstrip() for line in display_lines]
        
        # 2. 末尾の空行を削除
        while processed_lines and not processed_lines[-1]:
            processed_lines.pop()
            
        content = "\n".join(processed_lines)
        
        # 3. カーソル位置の補正
        # pyte の cursor.y/x は 0-indexed
        orig_y = self._screen.cursor.y
        orig_x = self._screen.cursor.x

        # コンテンツが存在するならその範囲内に、空なら 0 に固定
        max_y = max(0, len(processed_lines) - 1)
        safe_line = max(0, min(orig_y, max_y))
        safe_col = max(0, orig_x)

        # 4. オブジェクトの構築
        # ConsoleSnapshot には「現在の表示領域のサイズ」を渡す
        console = ConsoleSnapshot(
            lines=self._lines,
            cols=self._cols,
            content=content
        )
        
        # CursorPosition の引数名は、クラスの定義（line, col）に合わせる
        cursor = CursorPosition(line=safe_line, col=safe_col)
        
        return Snapshot(timestamp=time.time(), cursor=cursor, console=console)
        

    # -------------------------
    # Internal
    # -------------------------

    def _read_loop(self) -> None:
        while self._pty.alive:
            data = self._pty.read(4096)
            if not data:
                time.sleep(0.01)
                continue
            self._stream.feed(data)

            if self._on_output:
                self._on_output()

        if self._on_exit:
            self._on_exit()