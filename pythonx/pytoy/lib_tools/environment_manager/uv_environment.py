from pytoy.lib_tools.environment_manager.models import ToolRunnerStrategyProtocol
from pytoy.lib_tools.environment_manager.models import EnvironmentKind

from dataclasses import dataclass
from typing import Sequence
from pytoy.lib_tools.utils import get_current_directory
import vim

import os
import subprocess
from pathlib import Path


@dataclass(frozen=True)
class UvStrategy(ToolRunnerStrategyProtocol):
    kind: EnvironmentKind = "uv"

    def wrap(self, arg: str | Sequence[str]):
        prefix = ["uv", "run"]
        if isinstance(arg, str):
            return f"{' '.join(prefix)} {arg}"
        return prefix + list(arg)


class UVEnvironmentSolver:
    def __init__(self):
        self._installed = None
        
    @property
    def kind(self) -> EnvironmentKind:
        return "uv"

    @property
    def installed(self) -> bool:
        import shutil
        if self._installed is not None:
            return self._installed
        ret =  bool(shutil.which("uv"))
        if ret:
            self._installed = True
        else:
            _add_uv_path_fallback()
            self._installed = bool(shutil.which("uv"))
        return self._installed

    def get_workspace(self, path: Path | str) -> Path | None:
        """If the path is wihtin the python project, then it returns 
        the root of workspace.  
        Note: This does not consider `workspace` fucntion of `uv`. 
        """
        if not self.installed:
            return None

        path = Path(path).resolve()
        for parent in [path] + list(path.parents):
            if (parent / "pyproject.toml").exists() or (parent / ".venv").is_dir():
                return parent
        return None


    def get_venv_path(self, path) -> Path | None:
        if path is None:
            path = get_current_directory()

        def _to_python_path() -> Path | None:
            ret = subprocess.run(
                'uv run python -c "import sys; print(sys.executable)"',
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=os.environ,
                cwd=path,
                text=True,
                shell=True,
            )
            if ret.returncode == 0:
                return Path(ret.stdout.strip())
            return None

        if not (python_path := _to_python_path()):
            # Maybe `bash` is not applied here.
            _add_uv_path_fallback()
            python_path = _to_python_path()
        if not python_path:
            return None

        if all(
            (python_path.parent / name).exists()
            for name in ["activate", "activate.bat"]
        ):
            # It should be virtual environment.
            return python_path.parent.parent
        else:
            # Not virtual environment.
            return None


__add_uv_path_fallback_tried = False
def _add_uv_path_fallback() -> bool:
    """
    side-effects: updating of `os.envioron['PATH']
    """
    global __add_uv_path_fallback_tried
    if __add_uv_path_fallback_tried:
        return False
    __add_uv_path_fallback_tried = True
    try:
        ret = subprocess.run(["bash", "-lic",  'which uv'], text=True, timeout=2.0, capture_output=True)
        if ret.returncode != 0:
            return False
        folder = Path(ret.stdout.strip()).parent.as_posix()
        current_path = os.environ.get('PATH', '')
        new_path = f"{folder}{os.pathsep}{current_path}"
        os.environ['PATH'] = new_path
        vim.command(f'let $PATH="{new_path}"')
        return True
    except Exception:
        return False