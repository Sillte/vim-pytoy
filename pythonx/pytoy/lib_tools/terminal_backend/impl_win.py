"""Terminal, which is used by python."""

from pathlib import Path
from typing import Sequence, Mapping
import winpty

from pytoy.lib_tools.utils import get_current_directory
from .protocol import (
    PseudoTerminalProtocol,
    PseudoTerminalProviderProtocol,
)


class PseudoTerminalWin(PseudoTerminalProtocol):
    def __init__(self, pty: winpty.PtyProcess):
        self.pty = pty

    def isalive(self) -> bool:
        return self.pty.isalive()

    @property
    def pid(self) -> int | None:
        return self.pty.pid

    def terminate(self) -> bool | None:
        return self.pty.terminate(force=True)

    def write(self, content: str) -> int:
        return self.pty.write(content)

    def readline(self) -> str | None:
        return self.pty.readline()


class PseudoTerminalProviderWin(PseudoTerminalProviderProtocol):
    def spawn(
        self,
        argv: str | Sequence[str],
        dimensions: tuple[int, int] | None = None,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> PseudoTerminalProtocol:
        if cwd is None:
            cwd = str(get_current_directory())
        pty = winpty.PtyProcess.spawn(argv, dimensions=dimensions, cwd=str(cwd), env=env)
        return PseudoTerminalWin(pty)


if __name__ == "__main__":
    pass
