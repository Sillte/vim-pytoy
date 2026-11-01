import sys
from pathlib import Path

from pytoy.devtools.dev_rebooter.models import RebootInfo
from pytoy.devtools.dev_rebooter.process import start_vim_detached
from pytoy.devtools.dev_rebooter.rebooter import RebooterWithInfoProtocol


class NVimRebooter(RebooterWithInfoProtocol):
    def __init__(self, root_folder: Path, *, minimal: bool = False, kill_myprocess: bool = True):
        self._root_folder = Path(root_folder)
        self._minimal = minimal
        self._kill_myprocess = kill_myprocess

    def prepare(self) -> RebootInfo:
        import vim

        cache_folder = Path(vim.eval("stdpath('cache')"))
        info = RebootInfo.from_cache_folder(cache_folder, self._root_folder)
        vim.command(f"let &runtimepath='{self._root_folder.as_posix()},' . &runtimepath")
        vim.command(f"mksession! {info.session_file.as_posix()}")
        return info

    def reboot(self, reboot_info: RebootInfo) -> None:
        import vim

        commands = ["nvim"]
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
        commands += ["-S", reboot_info.session_file.as_posix()]

        if sys.platform.startswith("win"):
            commands = ["start", "cmd", "/k"] + commands
        elif sys.platform.startswith("linux"):
            commands = ["x-terminal-emulator", "-e"] + commands
        else:
            raise RuntimeError("Unrecognized platform")

        start_vim_detached(commands)
        if self._kill_myprocess:
            vim.command("qall!")
