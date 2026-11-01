import json
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Self

from pytoy.tool_execution.execution_environment.uv_environment import UVEnvironmentSolver

JSON_CACHE_NAME = "pytoy_reboot.json"
SESSION_CACHE_NAME = "pytoy_reboot.vim"


@dataclass(frozen=True)
class RebootInfo:
    session_file: Path
    metafile_path: Path
    plugin_root_folder: Path
    debug_venv_path: Path | None = None

    @classmethod
    def from_cache_folder(cls, cache_folder: Path, plugin_root_folder: Path) -> Self:
        cache_folder.mkdir(parents=True, exist_ok=True)
        return cls(
            session_file=cache_folder / SESSION_CACHE_NAME,
            metafile_path=cache_folder / JSON_CACHE_NAME,
            plugin_root_folder=plugin_root_folder,
            debug_venv_path=UVEnvironmentSolver().find_venv_path(plugin_root_folder),
        )

    def dump(self) -> None:
        """Write reboot metadata for Vimscript consumers."""
        data = {
            "time": time(),
            "plugin_folder": self.plugin_root_folder.as_posix(),
            "debug_venv_path": self.debug_venv_path.as_posix() if self.debug_venv_path else None,
        }
        self.metafile_path.parent.mkdir(parents=True, exist_ok=True)
        self.metafile_path.write_text(json.dumps(data, indent=4))
