import os
from pathlib import Path

from pytoy.shared.lib.backend import BackendEnum, get_backend_enum


class GlobalStorage:
    """Provide persistent application data for the active editor backend."""

    STORAGE_ROOT_NAME = "vim_pytoy"
    LOG_DIRECTORY = "_logs"
    LOG_FILE_NAME = "global.log"

    def __init__(self, storage_root: str | Path | None = None):
        self._storage_root = Path(storage_root).expanduser().resolve() if storage_root else self._resolve_storage_root()

    @property
    def storage_root(self) -> Path:
        self._storage_root.mkdir(exist_ok=True, parents=True)
        return self._storage_root

    def resolve_path(self, relative_path: str | Path = "") -> Path:
        """Return a path below the global storage root."""
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

    @classmethod
    def _resolve_storage_root(cls) -> Path:
        # TODO: Consider to acquire dynamically the configuration directory.
        # If the current specification is preferred, then please remove this comment.
        backend = get_backend_enum()
        if backend in {BackendEnum.NVIM, BackendEnum.VSCODE}:
            return cls._resolve_nvim_config_root() / os.environ.get("NVIM_APPNAME", "nvim") / cls.STORAGE_ROOT_NAME
        elif backend == BackendEnum.VIM:
            if os.name == "nt":
                candidates = ("vimfiles", ".vim")
            else:
                candidates = (".vim", "vimfiles")
            for cand in candidates:
                vim_root = Path.home() / cand
                if vim_root.exists():
                    return vim_root / cls.STORAGE_ROOT_NAME
            vim_root = Path.home() / ("vimfiles" if os.name == "nt" else ".vim")
            return vim_root / cls.STORAGE_ROOT_NAME
        else:
            config_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
            return config_root / cls.STORAGE_ROOT_NAME

    @staticmethod
    def _resolve_nvim_config_root() -> Path:
        config_home = os.environ.get("XDG_CONFIG_HOME")
        if config_home:
            return Path(config_home)
        if os.name == "nt":
            return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return Path.home() / ".config"
