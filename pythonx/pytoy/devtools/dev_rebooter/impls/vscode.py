from pathlib import Path

from pytoy.devtools.dev_rebooter.models import RebootInfo
from pytoy.devtools.dev_rebooter.rebooter import RebooterWithInfoProtocol


class VSCodeRebooter(RebooterWithInfoProtocol):
    def __init__(self, root_folder: Path, *, minimal: bool = False, kill_myprocess: bool = True):
        self._root_folder = Path(root_folder)

    def prepare(self) -> RebootInfo:
        import vim

        cache_folder = Path(vim.eval("stdpath('cache')"))
        info = RebootInfo.from_cache_folder(cache_folder, self._root_folder)
        vim.command(f"let &runtimepath='{self._root_folder.as_posix()},' . &runtimepath")
        vim.command(f"mksession! {info.session_file.as_posix()}")
        return info

    def reboot(self, reboot_info: RebootInfo) -> None:
        from pytoy.shared.ui.vscode.api import Api

        Api().action("vscode-neovim.restart")
