import hashlib
import logging
from pathlib import Path
from typing import Self

from pytoy.shared.loggers import setup_logger

from .workspace_discovery import find_workspace


class WorkspaceStorage:
    """Provide a private, persistent data area for one workspace."""

    STORAGE_ROOT_NAME = ".pytoy"
    LOG_DIRECTORY = "_logs"
    LOG_FILE_NAME = "workspace.log"

    def __init__(self, workspace: str | Path):
        self._workspace = Path(workspace).expanduser().resolve()

    @classmethod
    def from_path(cls, start_path: str | Path) -> Self:
        """Create storage for the workspace containing ``start_path``."""
        return cls(find_workspace(start_path))

    @staticmethod
    def find_workspace(start_path: str | Path) -> Path:
        """Return the workspace containing ``start_path``."""
        return find_workspace(start_path)

    @property
    def workspace(self) -> Path:
        return self._workspace

    @property
    def storage_root(self) -> Path:
        root = self._workspace / self.STORAGE_ROOT_NAME
        root.mkdir(exist_ok=True, parents=True)
        return root

    def resolve_path(self, relative_path: str | Path = "") -> Path:
        """Return a path below the workspace's private data root."""
        candidate = (self.storage_root / Path(relative_path)).resolve()
        try:
            candidate.relative_to(self.storage_root)
        except ValueError as exc:
            raise ValueError(f"Path must stay inside {self.storage_root}: {relative_path}") from exc
        return candidate

    def ensure_directory(self, relative_path: str | Path = "") -> Path:
        directory = self.resolve_path(relative_path)
        directory.mkdir(exist_ok=True, parents=True)
        return directory

    @property
    def log_path(self) -> Path:
        return self.resolve_path(self.LOG_DIRECTORY) / self.LOG_FILE_NAME

    def get_logger(self, level: int | None = None) -> logging.Logger:
        logger_name = self._make_logger_name()
        return setup_logger(logger_name, self.log_path, enable_console=False, level=level)

    def is_logger_exist(self) -> bool:
        logger_name = self._make_logger_name()
        return logger_name in logging.root.manager.loggerDict and bool(logging.getLogger(logger_name).handlers)

    def _make_logger_name(self) -> str:
        workspace_hash = hashlib.sha1(str(self.workspace).encode("utf8")).hexdigest()[:8]
        return f"pytoy.workspace.{self.workspace.name}.{workspace_hash}"
