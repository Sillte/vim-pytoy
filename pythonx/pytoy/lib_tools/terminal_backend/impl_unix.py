"""Terminal, which is used by python."""

from pathlib import Path
from typing import Sequence, Mapping
import pexpect

from pytoy.lib_tools.utils import get_current_directory

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
        env: Mapping[str, str] | None = None,
    ) -> PseudoTerminalProtocol:
        if isinstance(argv, Sequence) and (not isinstance(argv, str)):
            command = argv[0]
            argv = list(argv[1:])
        elif isinstance(argv, str):
            command = argv
            argv = []
        else:
            raise RuntimeError("Implementation Error")
        assert isinstance(command, str)
        assert isinstance(argv, list)

        if cwd is None:
            cwd = get_current_directory()
            
        if env is not None:
            raise NotImplementedError("env is not `None` case is not implemented yet.")
        try:
            pty = pexpect.spawn(
                command, argv, cwd=cwd, env=env, encoding="utf-8", dimensions=dimensions
            )
        except Exception as e:
            _add_path_fallback(command)
            pty = pexpect.spawn(
                command, argv, cwd=cwd, env=env, encoding="utf-8", dimensions=dimensions
            )
        return PseudoTerminalUnix(pty)
    

    
def _add_path_fallback(command: str) -> bool:
    """
    side-effects: updating of `os.envioron['PATH']
    """
    import subprocess
    import os
    import vim
    ret = subprocess.run(f"bash -lic 'which {command}'", shell=True, stdout=subprocess.PIPE, text=True)
    if ret.returncode != 0:
        return False
    first_line = ret.stdout.strip().split("\n")[0]
    folder = Path(first_line).parent.as_posix()
    current_path = os.environ.get('PATH', '')
    new_path = f"{folder}{os.pathsep}{current_path}"
    os.environ['PATH'] = new_path
    vim.command(f'let $PATH="{new_path}"')
    return True


if __name__ == "__main__":
    pass
