from __future__ import annotations

import shlex
from pathlib import Path
from typing import Mapping, Protocol, runtime_checkable


@runtime_checkable
class PtyConsoleProtocol(Protocol):
    """PtyConsoleが提供すべきインターフェースの定義"""

    def start(self) -> None: ...
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
        self, cmd: str | list[str], cwd: str | Path | None, size: tuple[int, int], env: Mapping[str, str] | None = None
    ):
        from winpty import PtyProcess  # ty: ignore[unresolved-import]

        self._cmd = cmd
        self._cwd = str(cwd) if cwd else None
        self._env = env
        self._size = size
        self._proc: PtyProcess | None = None

    def start(self) -> None:
        from winpty import PtyProcess  # ty: ignore[unresolved-import]

        if self._proc is not None:
            raise RuntimeError("Already started.")

        self._proc = PtyProcess.spawn(
            self._cmd,
            cwd=self._cwd,
            env=self._env,
            dimensions=self._size,
        )

    @property
    def proc(self):
        if self._proc is None:
            raise RuntimeError("It is not yet started.")
        return self._proc

    def read(self, size: int = 4096) -> str:
        try:
            return self.proc.read(size)
        except EOFError:
            return ""

    def write(self, data: str):
        self.proc.write(data)

    def resize(self, lines: int, cols: int):
        self.proc.setwinsize(lines, cols)
        self._size = (lines, cols)

    def send_ctrl_c(self):
        """Unfortunately, this does not work in the environment
        VSCode + neovim extension.
        """
        from pytoy.tool_execution.terminal.infra.runner.impls.utils import find_children
        from pytoy.tool_execution.terminal.infra.runner.impls.utils import send_ctrl_c as func

        self.proc.write("\x03\x03\x03")
        if self.pid:
            func(self.pid)
            for elem in find_children(self.pid):
                func(elem)

    def terminate(self):
        if self._proc is not None:
            self._proc.terminate()
            self._proc = None

    @property
    def alive(self) -> bool:
        if self._proc is None:
            return False
        return self._proc.isalive()

    @property
    def pid(self) -> int | None:
        if self._proc is None:
            return None
        return self._proc.pid

    @property
    def size(self) -> tuple[int, int]:
        if self._proc is None:
            return self._size
        return self._proc.getwinsize()


class PosixPtyAdapter(PtyConsoleProtocol):
    def __init__(
        self, cmd: str | list[str], cwd: str | Path | None, size: tuple[int, int], env: Mapping[str, str] | None = None
    ):
        # リスト形式なら安全にクォートして結合、文字列ならそのまま使用
        if isinstance(cmd, list):
            cmd_str = " ".join(shlex.quote(arg) for arg in cmd)
        else:
            cmd_str = cmd
        self._cmd = cmd_str
        self._env = env
        self._size = size

        self._cwd = str(cwd) if cwd else None
        self._proc = None

    def start(self) -> None:
        from pexpect import spawn  # ty: ignore[unresolved-import]

        if self._proc is not None:
            raise RuntimeError("Already started.")

        self._proc = spawn(
            self._cmd,
            cwd=self._cwd,
            env=self._env,
            dimensions=self._size,
        )

    @property
    def proc(self):
        if self._proc is None:
            raise RuntimeError("It is not yet started.")
        return self._proc

    def read(self, size: int = 4096) -> str:
        import pexpect  # ty: ignore[unresolved-import]

        try:
            # POSIXでは非ブロッキング読み取りとUTF-8変換を適用
            return self.proc.read_nonblocking(size, timeout=0.1).decode("utf-8", "replace")
        except (pexpect.TIMEOUT, pexpect.EOF):
            return ""

    def write(self, data: str) -> None:
        self.proc.send(data)

    def resize(self, lines: int, cols: int) -> None:
        self.proc.setwinsize(lines, cols)
        self._size = (lines, cols)

    def send_ctrl_c(self):
        # POSIXにおける Ctrl+C 送信
        self.proc.sendcontrol("c")

    def terminate(self) -> None:
        if self._proc is not None:
            self._proc.terminate(force=True)
            self._proc = None

    @property
    def alive(self) -> bool:
        if self._proc is None:
            return False
        return self._proc.isalive()

    @property
    def pid(self) -> int | None:
        if self._proc is None:
            return None
        return self._proc.pid

    @property
    def size(self) -> tuple[int, int]:
        if self._proc:
            return self._proc.getwinsize()
        return self._size


# --- Facade ---


class PtyConsole:
    """
    OSごとのPty実装を隠蔽するFacadeクラス。
    """

    def __new__(
        cls, cmd: str | list[str], cwd: str | Path | None, size: tuple[int, int], env: Mapping[str, str] | None = None
    ) -> PtyConsoleProtocol:
        # WindowsかPOSIXかを判定して適切なAdapterを返す
        import platform

        system = platform.system()

        if system == "Windows":
            adapter_class = WinPtyAdapter
        elif system == "Linux":
            adapter_class = PosixPtyAdapter
        else:
            raise NotImplementedError(f"Unsupported platform: {system}")
        return adapter_class(cmd, cwd, size, env)
