# """EnvironmentManager.
# This class handles the properties related to the `env` parameters of `subprocess`.
# As of 2026/01, this class handles `uv`.
# """

from pathlib import Path
from typing import  Literal, assert_never, Sequence, Self
from pytoy.lib_tools.environment_manager.models import EnvironmentSolverProtocol, SystemEnvironmentSolver
from pytoy.lib_tools.environment_manager.models import SystemStrategy
from pytoy.lib_tools.environment_manager.uv_environment import UvStrategy
from pytoy.lib_tools.environment_manager.uv_environment import UVEnvironmentSolver
import vim
from pytoy.lib_tools.utils import get_current_directory
from dataclasses import dataclass
from pytoy.lib_tools.environment_manager.models import EnvironmentKind, ExecutionPreference, CommandWrapperType, ExecutionWrapperType
from pytoy.lib_tools.environment_manager.models import ToolRunnerStrategyProtocol


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


class EnvironmentManager:
    """This class stores the information regarding the entire application,
    without the knowledge of `vim` / `nvim` / `vscode`. 
    
    """
    def __init__(self, ):
        self._execution_preference: ExecutionPreference = "auto"
        # NOTE: The order of dict represents the preference.
        # That is, "system" must be the last element of the `_solvers`.
        self._solvers : dict[EnvironmentKind, EnvironmentSolverProtocol] = {
            "uv": UVEnvironmentSolver(), 
        }
        self._solvers["system"] = SystemEnvironmentSolver()
    
    @property
    def installed_kinds(self) -> Sequence[EnvironmentKind]:
        return [key for key, solver in self._solvers.items() if solver.installed]

    @property
    def execution_preference(self):
        return self._execution_preference

    @property 
    def available_execution_preferences(self) -> Sequence[ExecutionPreference]:
        base_prefs: list[ExecutionPreference] = ["auto"]
        return list(self.installed_kinds) +  base_prefs

    
    def set_execution_preference(self, preference: ExecutionPreference):
        self._execution_preference = preference
        
    def solve_preference(self, path: Path | str, preference: ExecutionPreference | None = None) -> ResolvedExecutionEnvironment:
        preference = preference or self._execution_preference

        path = Path(path)
        solver, workspace = self._get_appropriate_solver(path, preference)
        if solver:
            strategy =ToolRunnerStrategy.from_kind(solver.kind)
            return ResolvedExecutionEnvironment(strategy, workspace=workspace, base_path=path)
        strategy = ToolRunnerStrategy.from_kind("system")
        return ResolvedExecutionEnvironment(strategy, workspace=None, base_path=path)

    def get_workspace(self, start_path: str | Path, preference: None | EnvironmentKind | Literal["auto"] = "system") -> None | Path:
        start_path = Path(start_path).resolve()
        _, workspace = self._get_appropriate_solver(start_path, preference)
        return workspace


        
    def _get_appropriate_solver(self, path: str | Path, preference: None | EnvironmentKind | Literal["auto"]) -> tuple[None | EnvironmentSolverProtocol, None | Path]:
        if preference is None or preference == "auto":
            for solver in self._solvers.values():
                if solver.installed and (workspace:= solver.get_workspace(path)):
                    return solver, workspace
        elif preference in self._solvers:
            solver = self._solvers[preference]
            return solver, solver.get_workspace(path)
        return None, None


if __name__ == "__main__":
    pass

