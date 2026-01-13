from __future__ import annotations
import shlex
from pathlib import Path
from typing import Protocol, runtime_checkable

@runtime_checkable
class PtyConsoleProtocol(Protocol):
    """PtyConsoleが提供すべきインターフェースの定義"""
    def read(self, size: int = 4096) -> str: ...
    def write(self, data: str) -> None: ...
    def resize(self, lines: int, cols: int) -> None: ...
    def send_ctrl_c(self) -> None: ...
    def terminate(self) -> None: ...
    
    @property
    def alive(self) -> bool: ...
    @property
    def pid(self) -> int | None: ...
    @property
    def size(self) -> tuple[int, int]: ...

# --- Adapters ---

class WinPtyAdapter(PtyConsoleProtocol):
    def __init__(
        self, 
        cmd: str | list[str], 
        cwd: str | Path | None, 
        size: tuple[int, int], 
        env: dict[str, str] | None = None
    ):
        from winpty import PtyProcess
        # Pathオブジェクトを文字列に正規化
        str_cwd = str(cwd) if cwd else None
        
        self._proc = PtyProcess.spawn(
            cmd, 
            cwd=str_cwd, 
            env=env, 
            dimensions=size,
        )
        self._size = size

    def read(self, size: int = 4096) -> str:
        try:
            return self._proc.read(size)
        except EOFError:
            return ""

    def write(self, data: str):
        self._proc.write(data)

    def resize(self, lines: int, cols: int):
        self._proc.setwinsize(lines, cols)
        self._size = (lines, cols)

    def send_ctrl_c(self):
        """Unfortunately, this does not work in the environment
        VSCode + neovim extension. 
        """
        from pytoy.lib_tools.terminal_runner.impls.utils import send_ctrl_c as func
        from pytoy.lib_tools.terminal_runner.impls.utils import find_children

        self._proc.write("\x03\x03\x03")
        if self.pid:
            func(self.pid)
            for elem in find_children(self.pid):
                func(elem)

    def terminate(self):
        self._proc.terminate()

    @property
    def alive(self) -> bool:
        return self._proc.isalive()

    @property
    def pid(self) -> int | None:
        return self._proc.pid

    @property
    def size(self) -> tuple[int, int]:
        return self._proc.getwinsize()


class PosixPtyAdapter(PtyConsoleProtocol):
    def __init__(
        self, 
        cmd: str | list[str], 
        cwd: str | Path | None, 
        size: tuple[int, int], 
        env: dict[str, str] | None = None
    ):
        import pexpect
        # リスト形式なら安全にクォートして結合、文字列ならそのまま使用
        if isinstance(cmd, list):
            cmd_str = " ".join(shlex.quote(arg) for arg in cmd)
        else:
            cmd_str = cmd
            
        str_cwd = str(cwd) if cwd else None
            
        self._proc = pexpect.spawn(cmd_str, cwd=str_cwd, env=env, dimensions=size)

    def read(self, size: int = 4096) -> str:
        try:
            # POSIXでは非ブロッキング読み取りとUTF-8変換を適用
            return self._proc.read_nonblocking(size, timeout=0.1).decode('utf-8', 'replace')
        except (pexpect.TIMEOUT, pexpect.EOF):
            return ""

    def write(self, data: str):
        self._proc.send(data)

    def resize(self, lines: int, cols: int):
        self._proc.setwinsize(lines, cols)

    def send_ctrl_c(self):
        # POSIXにおける Ctrl+C 送信
        self._proc.sendcontrol('c')

    def terminate(self):
        self._proc.terminate(force=True)

    @property
    def alive(self) -> bool:
        return self._proc.isalive()

    @property
    def pid(self) -> int | None:
        return self._proc.pid

    @property
    def size(self) -> tuple[int, int]:
        return self._proc.getwinsize()

# --- Facade ---

class PtyConsole:
    """
    OSごとのPty実装を隠蔽するFacadeクラス。
    """
    def __new__(
        cls, 
        cmd: str | list[str], 
        cwd: str | Path | None, 
        size: tuple[int, int], 
        env: dict[str, str] | None = None
    ) -> PtyConsoleProtocol:
        # WindowsかPOSIXかを判定して適切なAdapterを返す
        import platform
        adapter_class = WinPtyAdapter if platform.system() == 'Windows' else PosixPtyAdapter
        return adapter_class(cmd, cwd, size, env)