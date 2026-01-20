# """EnvironmentManager.
# This class handles the properties related to the `env` parameters of `subprocess`.
# As of 2025/05, this class handles `uv` and `virtualenv`.
# """

import os
from pathlib import Path
from typing import Callable, Literal, Any, Protocol, assert_never
import subprocess
from enum import Enum
import vim
from pytoy.ui import lightline_utils
from pytoy.lib_tools.utils import get_current_directory
from dataclasses import dataclass

DefaultEnvironment = Literal["system"]
type EnvironmentKind = Literal["uv"] | DefaultEnvironment
# `naive` use `command` as is, `auto`, solves the apt evnrionment from `cwd`.
type ExecutionPreference =  Literal["auto"]  | EnvironmentKind 


class UvMode(str, Enum):
    UNDEFINED = "undefined"
    ON = "on"
    OFF = "off"
    
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

@dataclass(frozen=True)
class ExecutionEnvironment:
    kind: EnvironmentKind
    workspace: Path | None = None
    warning: str | None = None
    
    @property
    def command_wrapper(self) -> Callable[[str | list[str] | tuple[str]], list[str] | str]:
        def wrap(arg: str | list[str] | tuple[str]) -> list[str] | str:
            match self.kind:
                case "system":
                    prefix = []
                case "uv":
                    prefix = ["uv", "run"]
                case _:
                    assert_never(self.kind)
            if isinstance(arg, str):
                full_prefix = " ".join(prefix)
                return f"{full_prefix} {arg}".strip()
            else:
                return prefix + list(arg)
        return wrap

class EnvironmentSolverProtocol(Protocol):
    @property
    def installed(self) -> bool: ...
    def get_workspace(self, path: str | Path, /) -> Path | None : ...

class UVEnvironmentSolver:
    def __init__(self):
        self._installed = None
        
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


class EnvironmentManager:
    """This class stores the information regarding the entire application,
    without the knowledge of `vim` / `nvim` / `vscode`. 
    
    """
    def __init__(self, ):
        self._execution_preference: ExecutionPreference = "auto"
        self._solvers : dict[EnvironmentKind, EnvironmentSolverProtocol] = {
            "uv": UVEnvironmentSolver()
        }
    
    @property
    def installed_kinds(self) -> list[EnvironmentKind]:
        return [key for key, solver in self._solvers.items() if solver.installed]

    @property
    def execution_preference(self):
        return self._execution_preference
    
    def set_execution_preference(self, preference: ExecutionPreference):
        self._execution_preference = preference
        
    def solve_preference(self, path: Path | str, preference: ExecutionPreference | None = None) -> ExecutionEnvironment:
        preference = preference or self._execution_preference
        installed_kinds = self.installed_kinds
        if preference in self._solvers: # The case for setting the environment directly.
            if preference in installed_kinds:
                workspace = self._solvers[preference].get_workspace(path)
                if workspace:
                    return ExecutionEnvironment(kind=preference, workspace=workspace)
                else:
                    return ExecutionEnvironment(kind=preference, workspace=workspace, warning="NonWorkspace")
            else:
                msg = f"`{preference=}` is not installed."
                raise ValueError(msg)
        match preference:
            case "system":
                return ExecutionEnvironment(kind="system")
            case "auto":
                for kind in installed_kinds:
                    workspace = self._solvers[kind].get_workspace(path)
                    if workspace:
                        return ExecutionEnvironment(kind=kind, workspace=workspace)
                else:
                    return ExecutionEnvironment(kind="system")
        raise RuntimeError("Invalid Specication of `{preference=}`")


class OldEnvironmentManager:
    # Singleton.(Thread unsafe.)
    __cache = None

    def __new__(cls):
        if cls.__cache is None:
            self = object.__new__(cls)
            cls.__cache = self
            self._init()
        else:
            self = cls.__cache
        return self

    def _init(self):
        self._uv_mode = UvMode.UNDEFINED
        self._prev_venv_path = None

    def get_uv_venv(self, path: str | Path | None = None) -> Path | None:
        """Return the environment `uv run` uses if it has virtual envrinment.

        # [TODO] handling of `--package`.
        """
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

    def get_command_wrapper(
        self, force_uv: bool | None = False
    ) -> Callable[[str], str]:
        # [NOTE]: In the future, parameter may become desirable.
        # Consider `--package option`

        if force_uv is True or self.get_uv_mode() == UvMode.ON:
            return lambda cmd: f"uv run {cmd}"
        else:
            return lambda cmd: cmd

    def on_uv_mode_on(self):
        """Hook function when `uv_mode` becomes on.
        Handling the global state of VIM.
        """

        uv_mode = "uv-mode"
        if not lightline_utils.is_registered(uv_mode):
            lightline_utils.register(uv_mode)
        # Change the environment of `JEDI`.
        venv_path = self.get_uv_venv()
        prev_path = vim.vars.get("g:jedi#environment_path")
        if prev_path:
            self._prev_venv_path = prev_path
        if venv_path:
            vim.vars["g:jedi#environment_path"] = venv_path.as_posix()

    def on_uv_mode_off(self):
        """Hook function when `uv_mode` becomes off.
        Handling the global state of VIM.
        """

        uv_mode = "uv-mode"
        if lightline_utils.is_registered(uv_mode):
            lightline_utils.deregister(uv_mode)

        # Change the environment of `JEDI`.
        if self._prev_venv_path:
            vim.vars["g:jedi#environment_path"] = self._prev_venv_path
        else:
            vim.vars["g:jedi#environment_path"] = "auto"

    def set_uv_mode(self, uv_mode: UvMode):
        prev_mode = self._uv_mode
        self._uv_mode = uv_mode
        if prev_mode != uv_mode and self._uv_mode == UvMode.ON:
            self.on_uv_mode_on()
        elif prev_mode != uv_mode and self._uv_mode == UvMode.OFF:
            self.on_uv_mode_off()
        return self._uv_mode

    def get_uv_mode(self):
        if self._uv_mode == UvMode.UNDEFINED:
            if self.get_uv_venv():
                self.set_uv_mode(UvMode.ON)
            else:
                self.set_uv_mode(UvMode.OFF)
        return self._uv_mode

    def toggle_uv_mode(self):
        if self._uv_mode == UvMode.UNDEFINED:
            return self.get_uv_mode()
        if self._uv_mode == UvMode.ON:
            return self.set_uv_mode(UvMode.OFF)
        else:
            return self.set_uv_mode(UvMode.ON)
        

def term_start():
    import sys
    from pytoy.ui.utils import to_filepath
    from pytoy.ui.ui_enum import get_ui_enum, UIEnum
    if get_ui_enum() != UIEnum.VIM:
        raise ValueError("This funciton is only for `VIM`.")
    
    venv_folder = OldEnvironmentManager().get_uv_venv()
    if not venv_folder:
        raise ValueError("Cannot find the `venv_folder`.")
    if sys.platform == "win32":

        activate_path = venv_folder / "Scripts" / "activate"
    else:
        activate_path = venv_folder / "bin" / "activate"

    number = vim.eval(r"term_start(&shell)")

    def _to_slash_path(path):
        path = Path(path)
        result = str(path).replace("\\", "/")
        return result

    path = _to_slash_path(activate_path)
    keys = rf"{_to_slash_path(path)} \<CR>"
    vim.eval(rf'term_sendkeys({number}, "{keys}")')


if __name__ == "__main__":
    manager = OldEnvironmentManager()

