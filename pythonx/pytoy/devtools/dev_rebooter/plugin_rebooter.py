from pathlib import Path

from pytoy.devtools.dev_rebooter.models import JSON_CACHE_NAME, SESSION_CACHE_NAME
from pytoy.devtools.dev_rebooter.rebooter import create_rebooter_for_current_backend
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from pytoy.tool_execution.execution_environment.uv_environment import UVEnvironmentSolver


class PluginRebooter:
    """Detect a plugin's Python workspace and provide its restart operation."""

    JSON_CACHE_NAME = JSON_CACHE_NAME
    SESSION_CACHE_NAME = SESSION_CACHE_NAME

    def __init__(self, start_folder: str | Path | None = None):
        if start_folder is None:
            current_buffer = PytoyBuffer.get_current()
            if current_buffer.source.type == "file" and current_buffer.file_path:
                start_folder = current_buffer.file_path
            else:
                start_folder = Path.cwd()

        root_folder = UVEnvironmentSolver().find_workspace(start_folder)
        if root_folder is None:
            raise ValueError(f"The given folder is NOT plugin:{start_folder=}")
        self._root_folder = root_folder

    @property
    def root_folder(self) -> Path:
        return self._root_folder

    def restart(self, minimal: bool = False) -> None:
        """Write reboot artifacts and restart the active editor backend."""
        rebooter = create_rebooter_for_current_backend(self._root_folder, minimal=minimal)
        reboot_info = rebooter.prepare()
        reboot_info.dump()
        rebooter.reboot(reboot_info)
