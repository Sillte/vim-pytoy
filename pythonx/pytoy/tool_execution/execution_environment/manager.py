from pathlib import Path
from typing import Literal, Sequence

from .models import (
    EnvironmentKind,
    EnvironmentSolverProtocol,
    ExecutionPreference,
    SystemEnvironmentSolver,
)
from .runner_strategy import ResolvedExecutionEnvironment, ToolRunnerStrategy
from .uv_environment import UVEnvironmentSolver


class EnvironmentManager:
    """This class stores the information regarding the entire application,
    without the knowledge of `vim` / `nvim` / `vscode`.

    """

    def __init__(
        self,
    ):
        self._execution_preference: ExecutionPreference = "auto"
        # NOTE: The order of dict represents the preference.
        # That is, "system" must be the last element of the `_solvers`.
        self._solvers: dict[EnvironmentKind, EnvironmentSolverProtocol] = {
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
        return list(self.installed_kinds) + base_prefs

    def set_execution_preference(self, preference: ExecutionPreference):
        self._execution_preference = preference

    def solve_preference(
        self, path: Path | str, preference: ExecutionPreference | None = None
    ) -> ResolvedExecutionEnvironment:
        preference = preference or self._execution_preference

        path = Path(path)
        solver, workspace = self._get_appropriate_solver(path, preference)
        if solver:
            strategy = ToolRunnerStrategy.from_kind(solver.kind)
            return ResolvedExecutionEnvironment(strategy, workspace=workspace, base_path=path)
        strategy = ToolRunnerStrategy.from_kind("system")
        return ResolvedExecutionEnvironment(strategy, workspace=None, base_path=path)

    def find_workspace(
        self, start_path: str | Path, preference: None | EnvironmentKind | Literal["auto"] = "system"
    ) -> None | Path:
        start_path = Path(start_path).resolve()
        _, workspace = self._get_appropriate_solver(start_path, preference)
        return workspace

    def find_project(
        self, start_path: str | Path, preference: None | EnvironmentKind | Literal["auto"] = "system"
    ) -> None | Path:
        start_path = Path(start_path).resolve()
        solver, _ = self._get_appropriate_solver(start_path, preference)
        if solver:
            return solver.find_project(start_path)
        return None

    def _get_appropriate_solver(
        self, path: str | Path, preference: None | EnvironmentKind | Literal["auto"]
    ) -> tuple[None | EnvironmentSolverProtocol, None | Path]:
        if preference is None or preference == "auto":
            for solver in self._solvers.values():
                if solver.installed and (workspace := solver.find_workspace(path)):
                    return solver, workspace
        elif preference in self._solvers:
            solver = self._solvers[preference]
            return solver, solver.find_workspace(path)
        return None, None
