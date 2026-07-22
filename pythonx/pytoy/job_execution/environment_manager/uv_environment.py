from functools import cache
from pytoy.job_execution.environment_manager.models import ToolRunnerStrategyProtocol, EnvironmentSolverProtocol
from pytoy.job_execution.environment_manager.models import EnvironmentKind

from dataclasses import dataclass
from typing import Sequence
from pytoy.job_execution.utils import get_current_directory

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


class UVEnvironmentSolver(EnvironmentSolverProtocol):
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
        ret = bool(shutil.which("uv"))
        if ret:
            self._installed = True
        else:
            _add_uv_path_fallback()
            self._installed = bool(shutil.which("uv"))
        return self._installed

    @cache
    def find_workspace(self, path: Path | str) -> Path | None:
        """If the path is within the python project, then it returns
        the root of workspace.
        """
        if not self.installed:
            return None
        candidate = None
        path = Path(path).resolve()
        for parent in [path] + list(path.parents):
            pyproject = parent / "pyproject.toml"
            if not pyproject.exists():
                continue
            candidate = parent
            if self._is_uv_workspace(pyproject):
                return candidate
        return candidate

    @cache
    def find_project(self, path: Path | str) -> Path | None:
        """If the path is within the python project, then it returns
        the root of workspace.
        Note: This does not consider `workspace` fucntion of `uv`.
        """
        if not self.installed:
            return None

        path = Path(path).resolve()
        for parent in [path] + list(path.parents):
            if (parent / "pyproject.toml").exists():
                return parent
        return None

    def _is_uv_workspace(self, pyproject: Path) -> bool:
        data = self._load_pyproject(pyproject)
        workspace = data.get("tool", {}).get("uv", {}).get("workspace")
        return isinstance(workspace, dict)

    @staticmethod
    @cache
    def _load_pyproject(path: Path) -> dict:
        import tomllib

        with path.open("rb") as f:
            data = tomllib.load(f)
        return data

    def find_venv_path(self, path: str | Path | None) -> Path | None:
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

        if all((python_path.parent / name).exists() for name in ["activate", "activate.bat"]):
            # It should be virtual environment.
            return python_path.parent.parent
        else:
            # Not virtual environment.
            return None


__add_uv_path_fallback_tried = False


def _add_uv_path_fallback() -> bool:
    """
    side-effects: updating of `os.environ['PATH']
    """
    global __add_uv_path_fallback_tried
    if __add_uv_path_fallback_tried:
        return False
    __add_uv_path_fallback_tried = True

    import shutil
    if bool(shutil.which("uv")):
        return True

    def _fetch_by_bash() -> None | str:
        ret = subprocess.run(["bash", "-lic", "command -v uv"], text=True, timeout=2.0, capture_output=True)
        if ret.returncode != 0:
            return None
        uv = Path(ret.stdout.strip())
        if uv.is_file():
            return uv.parent.as_posix()
        return None

    def _fetch_by_default() -> None | str:
        path = Path("~/.local/bin/uv").expanduser()
        if path.exists(): 
            return path.parent.as_posix()
        else:
            return None

    try:
        candidates = [_fetch_by_bash(), _fetch_by_default()]
        folder = next(
            (x for x in candidates if x is not None),
            None,
        )
        if folder is None:
            return False

        current_path = os.environ.get("PATH", "")
        paths = current_path.split(os.pathsep) if current_path else []
        if folder not in paths:
            paths.insert(0, folder)
        new_path = os.pathsep.join(paths)
        os.environ["PATH"] = new_path
        try:
            import vim
            vim.command(f'let $PATH="{new_path}"')
        except ImportError:
            pass
        return True
    except Exception:
        return False
