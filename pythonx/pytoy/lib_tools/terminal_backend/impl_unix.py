"""Terminal, which is used by python.
"""
from pathlib import Path
from typing import Sequence
import pexpect

from .protocol import (
    PseudoTerminalProtocol,
    PseudoTerminalProviderProtocol,
)


class PseudoTerminalUnix(PseudoTerminalProtocol):
    def __init__(self, pty: pexpect.spawn):
        self.pty = pty

    def isalive(self) -> bool:
        return self.pty.isalive()

    @property
    def pid(self) -> int | None:
        return self.pty.pid

    def terminate(self) -> bool | None:
        return self.pty.terminate(force=True)

    def write(self, content: str) -> int:
        return self.pty.send(content)

    def readline(self) -> str | None:
        try:
            return self.pty.readline()
        except pexpect.exceptions.TIMEOUT:
            return None


class PseudoTerminalProviderUnix(PseudoTerminalProviderProtocol):
    def spawn(
        self,
        argv: str | Sequence[str],
        dimensions: tuple[int, int] | None = None,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> PseudoTerminalProtocol:
        if isinstance(argv, Sequence) and (not isinstance(argv ,str)):
            command = argv[0]
            argv = list(argv[1:])
        elif isinstance(argv, str):
            command = argv
            argv = []
        else:
            raise RuntimeError("Implementation Error") 
        assert isinstance(command, str)
        assert isinstance(argv, list)
        pty = pexpect.spawn(command, argv, cwd=cwd, env=env, encoding="utf-8", dimensions=dimensions)
        return PseudoTerminalUnix(pty)


if __name__ == "__main__":
    pass
