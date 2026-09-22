import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Literal, assert_never

from pytoy.shared.loggers import setup_logger
from pytoy.shared.storage import WorkspaceStorage

from .readers import ConfigReader, ConfigWriter, FileReader, validate_safe_relative_path


class PytoyConfiguration:
    """Resolve and access project-local and user-global configuration."""

    NAME = "vim_pytoy"

    def __init__(self, local_folder: str | Path | None = None):
        self._global_folder = Path.home() / ".config" / self.NAME
        self._workspace_storage = WorkspaceStorage.from_path(local_folder or Path.cwd())

    @property
    def global_folder(self) -> Path:
        self._global_folder.mkdir(exist_ok=True, parents=True)
        return self._global_folder

    @property
    def local_folder(self) -> Path:
        return self._workspace_storage.storage_root

    @property
    def workspace_storage(self) -> WorkspaceStorage:
        return self._workspace_storage

    @property
    def file_reader(self) -> FileReader:
        return FileReader(self.local_folder, self.global_folder)

    @property
    def config_reader(self) -> ConfigReader:
        return ConfigReader(self.local_folder, self.global_folder)

    @property
    def config_writer(self) -> ConfigWriter:
        return ConfigWriter(self.local_folder, self.global_folder)

    def get_folder(self, relative_path: Path | str, location: Literal["global", "local"] = "local") -> Path:
        match location:
            case "local":
                return self._workspace_storage.ensure_directory(relative_path)
            case "global":
                base_folder = self._global_folder
                folder = validate_safe_relative_path(relative_path, base_folder)
                folder.mkdir(exist_ok=True, parents=True)
                return folder
            case _:
                assert_never(location)

    def _make_logger_name(self, location: Literal["global", "local"]) -> str:
        if location == "global":
            return "vim_pytoy.global"
        return self._workspace_storage.get_logger(level=None).name

    def get_logger(self, location: Literal["global", "local"] = "local", level: int | None = None) -> logging.Logger:
        match location:
            case "local":
                return self._workspace_storage.get_logger(level=level)
            case "global":
                log_path = self.get_folder("_logs", location="global") / "log.txt"
                return setup_logger(self._make_logger_name(location), log_path, enable_console=False, level=level)
            case _:
                assert_never(location)

    def is_logger_exist(self, location: Literal["global", "local"] = "local") -> bool:
        if location == "local":
            return self._workspace_storage.is_logger_exist()
        name = self._make_logger_name(location)
        return name in logging.root.manager.loggerDict and bool(logging.getLogger(name).handlers)

    def get_latest_log_path(self, location: Literal["global", "local"] | None = None) -> Path | None:
        """Return the latest log path for the requested or available scope."""
        if location is None:
            location = "local" if self.is_logger_exist("local") else "global"

        logger = self.get_logger(location)
        log_files: list[Path] = []
        for handler in logger.handlers:
            if not isinstance(handler, RotatingFileHandler):
                continue
            log_file = Path(handler.baseFilename)
            log_files.extend(log_file.parent.glob(f"{log_file.name}*"))
        if not log_files:
            return None
        return max(log_files, key=lambda path: path.stat().st_mtime)
