import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Protocol, Self, assert_never

from pytoy.shared.lib.backend import BackendEnum, get_backend_enum
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
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
    def from_cache_folder(cls, cache_folder: Path, plugin_root_folder) -> Self:
        cache_folder.mkdir(parents=True, exist_ok=True)
        session_file = cache_folder / SESSION_CACHE_NAME
        metafile_path = cache_folder / JSON_CACHE_NAME
        debug_venv_path = UVEnvironmentSolver().find_venv_path(plugin_root_folder)
        return cls(
            session_file=session_file,
            metafile_path=metafile_path,
            plugin_root_folder=plugin_root_folder,
            debug_venv_path=debug_venv_path,
        )

    def dump(self) -> None:
        """Dump the reboot information to the metafile."""
        data = {
            "time": time(),
            "plugin_folder": self.plugin_root_folder.as_posix(),
            "debug_venv_path": self.debug_venv_path.as_posix() if self.debug_venv_path else None,
        }
        self.metafile_path.parent.mkdir(parents=True, exist_ok=True)
        self.metafile_path.write_text(json.dumps(data, indent=4))


class RebooterWithInfoProtocol(Protocol):
    def prepare(self) -> RebootInfo: ...

    def reboot(self, reboot_info: RebootInfo) -> None: ...


class VimRebooter(RebooterWithInfoProtocol):
    def __init__(self, root_folder: Path, *, minimal: bool = False, kill_myprocess: bool = True):
        self._root_folder = Path(root_folder)
        self._minimal = minimal
        self._kill_myprocess = kill_myprocess

    def prepare(self) -> RebootInfo:
        import vim

        cach_folder = (
            Path(os.environ["XDG_CACHE_HOME"]) / "vim"
            if "XDG_CACHE_HOME" in os.environ
            else Path.home() / ".cache" / "vim"
        )
        info = RebootInfo.from_cache_folder(cach_folder, self._root_folder)
        vim.command(f"let &runtimepath='{self._root_folder.as_posix()},' . &runtimepath")
        vim.command(f"mksession! {info.session_file.as_posix()}")
        return info

    def reboot(self, reboot_info: RebootInfo):
        import vim

        if int(vim.eval("&term == 'builtin_gui'")):
            app = "gvim"
            is_gui = True
        else:
            app = "vim"
            is_gui = False

        commands = [app]

        if self._minimal:
            commands += ["-u", "NONE"]
        else:
            if reboot_info.debug_venv_path is not None:
                commands += ["--cmd", f"let g:pytoy_debug_venv='{reboot_info.debug_venv_path.as_posix()}'"]
            commands += ["--cmd", f"let g:pytoy_reboot='{reboot_info.plugin_root_folder.as_posix()}'"]
            commands += [
                "--cmd",
                f"let &runtimepath='{reboot_info.plugin_root_folder.as_posix()},' . &runtimepath",
            ]
        commands += ["-S", f"{reboot_info.session_file.as_posix()}"]

        if not is_gui:
            if sys.platform.startswith("win"):
                consoles = ["start", "cmd", "/k"]
            elif sys.platform.startswith("linux"):
                consoles = ["x-terminal-emulator", "-e"]
            else:
                raise RuntimeError("Unrecognized platform")
            commands = consoles + commands

        _start_vim_detached(commands)

        if self._kill_myprocess:
            vim.command("qall!")


class NVimRebooter(RebooterWithInfoProtocol):
    def __init__(self, root_folder: Path, *, minimal: bool = False, kill_myprocess: bool = True):
        self._root_folder = Path(root_folder)
        self._minimal = minimal
        self._kill_myprocess = kill_myprocess

    def prepare(self) -> RebootInfo:
        import vim

        cach_folder = Path(vim.eval("stdpath('cache')"))

        info = RebootInfo.from_cache_folder(cach_folder, self._root_folder)
        vim.command(f"let &runtimepath='{self._root_folder.as_posix()},' . &runtimepath")
        vim.command(f"mksession! {info.session_file.as_posix()}")
        return info

    def reboot(self, reboot_info: RebootInfo):
        import vim

        app = "nvim"
        _ = is_gui = False

        commands = [app]

        if self._minimal:
            commands += ["-u", "NONE"]
        else:
            if reboot_info.debug_venv_path is not None:
                commands += ["--cmd", f"let g:pytoy_debug_venv='{reboot_info.debug_venv_path.as_posix()}'"]
            commands += ["--cmd", f"let g:pytoy_reboot='{reboot_info.plugin_root_folder.as_posix()}'"]
            commands += [
                "--cmd",
                f"let &runtimepath='{reboot_info.plugin_root_folder.as_posix()},' . &runtimepath",
            ]
        commands += ["-S", f"{reboot_info.session_file.as_posix()}"]

        if not is_gui:
            if sys.platform.startswith("win"):
                console = ["start", "cmd", "/k"]
            elif sys.platform.startswith("linux"):
                console = ["x-terminal-emulator", "-e"]
            else:
                raise RuntimeError("Unrecognized platform")
            commands = console + commands

        _start_vim_detached(commands)

        if self._kill_myprocess:
            vim.command("qall!")


class VSCodeRebooter(RebooterWithInfoProtocol):
    def __init__(self, root_folder: Path, *, minimal: bool = False, kill_myprocess: bool = True):
        self._root_folder = Path(root_folder)
        self._minimal = minimal
        self._kill_myprocess = kill_myprocess

    def prepare(self) -> RebootInfo:
        import vim

        cach_folder = Path(vim.eval("stdpath('cache')"))

        info = RebootInfo.from_cache_folder(cach_folder, self._root_folder)
        vim.command(f"let &runtimepath='{self._root_folder.as_posix()},' . &runtimepath")
        vim.command(f"mksession! {info.session_file.as_posix()}")
        return info

    def reboot(self, reboot_info: RebootInfo):
        from pytoy.shared.ui.vscode.api import Api

        # NOTE:
        # Neovim is embedded in VSCode, so we cannot spawn a new process to restart directly.
        Api().action("vscode-neovim.restart")


class DummyRebooter(RebooterWithInfoProtocol):
    def __init__(self, root_folder: Path, *, minimal: bool = False, kill_myprocess: bool = True):
        self._root_folder = Path(root_folder)
        self._minimal = minimal
        self._kill_myprocess = kill_myprocess

    def prepare(self) -> RebootInfo:
        cach_folder = (
            Path(os.environ["XDG_CACHE_HOME"]) / "dummy_pytoy"
            if "XDG_CACHE_HOME" in os.environ
            else Path.home() / ".cache" / "dummy_pytoy"
        )

        info = RebootInfo.from_cache_folder(cach_folder, self._root_folder)
        return info

    def reboot(self, reboot_info: RebootInfo):
        _ = reboot_info
        pass


def create_rebooter_for_current_backend(root_folder: Path, *, minimal: bool = False) -> RebooterWithInfoProtocol:
    match get_backend_enum():
        case BackendEnum.VIM:
            return VimRebooter(root_folder, minimal=minimal)
        case BackendEnum.NVIM:
            return NVimRebooter(root_folder, minimal=minimal)
        case BackendEnum.VSCODE:
            return VSCodeRebooter(root_folder, minimal=minimal)
        case BackendEnum.DUMMY:
            return DummyRebooter(root_folder, minimal=minimal)
        case _:
            assert_never("Unrecognized backend enum.")


class VimPluginPackage:
    """Utility class for managing and developing Vim plugins.

    This class helps to detect the root directory of a Vim plugin
    and provides tools to restart Vim with the plugin correctly loaded.
    It supports automatic session saving and reinitialization during development.

    Attributes:
        root_folder (Path): The root directory of the detected Vim plugin package.
    """

    JSON_CACHE_NAME = "pytoy_reboot.json"
    SESSION_CACHE_NAME = "pytoy_reboot.vim"

    def __init__(self, start_folder: str | Path | None = None):
        """Initialize the package and detect its root directory.

        Args:
            start_folder (str | Path | None):
                The starting directory or file path to locate the Vim plugin root.
                If not specified, the current working directory is used.
        """
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

    def restart(self, minimal=False):
        """Write reboot cache files and restart the active Vim backend.

        Args:
            kill_myprocess (bool):
                If True, terminates the current Vim process after starting the new one.

        Note:
            This is useful when reinitializing plugin state during development,
            especially when changes affect runtime behavior or require a clean environment.
        """

        rebooter = create_rebooter_for_current_backend(self._root_folder, minimal=minimal)

        info = rebooter.prepare()
        info.dump()
        rebooter.reboot(info)


def _start_vim_detached(cmd):
    if sys.platform.startswith("win"):
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=DETACHED_PROCESS,
            shell=True,
        )
    else:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setpgrp,
            shell=False,
        )


if __name__ == "__main__":
    pass
