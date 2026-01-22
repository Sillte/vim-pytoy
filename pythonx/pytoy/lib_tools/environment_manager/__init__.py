# """EnvironmentManager.
# This class handles the properties related to the `env` parameters of `subprocess`.
# As of 2026/01, this class handles `uv`
# """

import os
from pathlib import Path
from typing import Callable, Literal, Protocol, assert_never, Sequence, overload, Self
import subprocess
import vim
from pytoy.lib_tools.utils import get_current_directory
from dataclasses import dataclass

DefaultEnvironment = Literal["system"]
type EnvironmentKind = Literal["uv"] | DefaultEnvironment
# `naive` use `command` as is, `auto`, solves the apt evnrionment from `cwd`.
type ExecutionPreference =  Literal["auto"]  | EnvironmentKind 


class CommandWrapperProtocol(Protocol):
    @overload
    def __call__(self, arg: str) -> str: ...
    
    @overload
    def __call__(self, arg: list[str] | tuple[str]) -> list[str]: ...

type CommandWrapperType = CommandWrapperProtocol
type ExecutionWrapperType = CommandWrapperType | ExecutionPreference


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

class ToolRunnerStrategyProtocol(Protocol):
    kind: EnvironmentKind

    @overload
    def wrap(self, arg: str) -> str: ...
    
    @overload
    def wrap(self, arg: Sequence[str]) -> list[str]: ...

    def wrap(self, arg: str | Sequence[str]) -> str | list[str]: ...

@dataclass(frozen=True)
class SystemStrategy(ToolRunnerStrategyProtocol):
    kind: EnvironmentKind = "system"

    def wrap(self, arg: str | Sequence[str]):
        return arg

@dataclass(frozen=True)
class UvStrategy(ToolRunnerStrategyProtocol):
    kind: EnvironmentKind = "uv"

    def wrap(self, arg: str | Sequence[str]):
        prefix = ["uv", "run"]
        if isinstance(arg, str):
            return f"{' '.join(prefix)} {arg}"
        return prefix + list(arg)


@dataclass(frozen=True)
class ToolRunnerStrategy:
    impl: ToolRunnerStrategyProtocol

    @property
    def kind(self) -> EnvironmentKind:
        return self.impl.kind

    @property
    def command_wrapper(self) -> CommandWrapperType:
        return self.impl.wrap

    @classmethod
    def from_kind(cls, environment_kind: EnvironmentKind) -> Self:
        match environment_kind:
            case "system":
                return cls(impl=SystemStrategy())
            case "uv":
                return cls(impl=UvStrategy())
            case _:
                assert_never(environment_kind)

@dataclass(frozen=True)
class ResolvedExecutionEnvironment:
    tool_runner_strategy: ToolRunnerStrategy
    workspace: Path | None
    base_path: Path

    @property
    def kind(self) -> EnvironmentKind:
        return self.tool_runner_strategy.kind

    @property
    def command_wrapper(self) -> CommandWrapperType:
        return self.tool_runner_strategy.command_wrapper


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

    @property 
    def available_execution_preferences(self) -> Sequence[ExecutionPreference]:
        base_prefs: list[ExecutionPreference] = ["auto", "system"]
        return list(self.installed_kinds) +  base_prefs

    
    def set_execution_preference(self, preference: ExecutionPreference):
        self._execution_preference = preference
        
    def solve_preference(self, path: Path | str, preference: ExecutionPreference | None = None) -> ResolvedExecutionEnvironment:
        preference = preference or self._execution_preference
        path = Path(path)

        installed_kinds = self.installed_kinds
        if preference in self._solvers: # The case for setting the environment directly.
            if preference in installed_kinds:
                workspace = self._solvers[preference].get_workspace(path)
                strategy = ToolRunnerStrategy.from_kind(preference)
                return ResolvedExecutionEnvironment(strategy, workspace=workspace, base_path=path)
            else:
                msg = f"`{preference=}` is not installed."
                raise ValueError(msg)

        match preference:
            case "system":
                strategy = ToolRunnerStrategy.from_kind("system")
                return ResolvedExecutionEnvironment(tool_runner_strategy=strategy, workspace=None, base_path=path)
            case "auto":
                for kind in installed_kinds:
                    workspace = self._solvers[kind].get_workspace(path)
                    if workspace:
                        strategy = ToolRunnerStrategy.from_kind(kind)
                        return ResolvedExecutionEnvironment(tool_runner_strategy=strategy, workspace=workspace, base_path=path)
                else:
                    strategy = ToolRunnerStrategy.from_kind("system")
                    return ResolvedExecutionEnvironment(tool_runner_strategy=strategy, workspace=workspace, base_path=path)
        raise RuntimeError("Invalid Specication of `{preference=}`")

    def get_workspace(self, start_path: str | Path, preference: None | EnvironmentKind | Literal["git", "auto"] = None) -> None | Path:
        def _get_workspace_based_on_git(start: Path) -> Path | None:
            for parent in [start] + list(start.parents):
                if (parent / ".git").exists():
                    return parent
            return None
        start_path = Path(start_path).resolve()

        if preference == "git":
            return _get_workspace_based_on_git(start_path)

        elif preference in self._solvers:
            return self._solvers[preference].get_workspace(start_path)

        # 3. 'auto' または None の場合（利用可能なソルバーを順次試し、最後に git を試す）
        elif preference == "auto" or preference is None:
            # まずは uv などのソルバー（プロジェクトファイル）で判定
            for solver in self._solvers.values():
                if solver.installed:
                    if (workspace := solver.get_workspace(start_path)):
                        return workspace
            return _get_workspace_based_on_git(start_path)
        else:
            raise ValueError(f"Invalid Argument, {preference=}")



def term_start():
    import sys
    from pytoy.ui.utils import to_filepath
    from pytoy.ui.ui_enum import get_ui_enum, UIEnum
    if get_ui_enum() != UIEnum.VIM:
        raise ValueError("This funciton is only for `VIM`.")
    
    start_path = get_current_directory()
    workspace = EnvironmentManager().get_workspace(start_path, preference="uv")
    if workspace:
        venv_folder = workspace / ".venv"
    else:
        venv_folder = None
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
    pass

