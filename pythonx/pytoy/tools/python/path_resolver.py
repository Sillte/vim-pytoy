from pytoy.contexts.core import GlobalCoreContext
from pytoy.job_execution.environment_manager import EnvironmentManager
from pytoy.job_execution.utils import get_current_directory


from pathlib import Path
from typing import Literal


class PathResolver:
    def __init__(self, environment_manager: EnvironmentManager | None = None, cwd: Path | None = None):
        self._environment_manager = environment_manager or GlobalCoreContext.get().environment_manager
        self._cwd = cwd

    @property
    def environment_manager(self) -> EnvironmentManager:
        return self._environment_manager

    @property
    def cwd(self) -> Path | None:
        return self._cwd

    def resolve(
        self, target: Literal["workspace", "current"] | str | Path | None, current_path: Path | None = None
    ) -> Path:
        if target is None:
            target = "current"
        current_directory = self._solve_current_directory(current_path)
        if target == "workspace":
            path = self.environment_manager.find_workspace(current_directory, "auto")
            if path is None:
                raise ValueError(f"`{current_directory=}` is NOT workspace.")
            return path
        elif target == "current":
            if current_path:
                return Path(current_path)
            else:
                return current_directory
        elif isinstance(target, (str, Path)):
            return Path(target)
        else:
            raise NotImplementedError(f"Not implmented for `{target=}`")

    def _solve_current_directory(self, current_path: Path | None) -> Path:
        if self.cwd:
            return self.cwd
        elif current_path is not None:
            return current_path.parent
        return get_current_directory()

    def to_workspace(self, current_path: Path | None) -> Path | None:
        current_directory = self._solve_current_directory(current_path)
        workspace = self.environment_manager.find_workspace(current_directory, preference="auto")
        return workspace

    def to_project(self, current_path: Path | None) -> Path | None:
        current_directory = self._solve_current_directory(current_path)
        project = self.environment_manager.find_project(current_directory, preference="auto")
        return project
