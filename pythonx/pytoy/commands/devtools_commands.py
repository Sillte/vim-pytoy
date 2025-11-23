from pathlib import Path
import time
import os
import json
import vim
from pytoy.command import CommandManager
from pytoy.infra.command.models import  OptsArgument
from pytoy.devtools.vimplugin_package import VimPluginPackage
from pytoy.devtools.vim_rebooter import VimRebooter
from pytoy.infra.timertask import TimerTask
from pytoy.ui import get_ui_enum, UIEnum
from pytoy.ui import to_filepath


class VimRebootExecutor:
    JSON_CACHE_NAME = "pytoy_reboot.json"
    SESSION_CACHE_NAME = "pytoy_reboot.vim"

    def __init__(self, start_folder=None):
        try:
            package = VimPluginPackage(start_folder)
        except ValueError as e:
            print("Current folder is not within a plugin folder.", e)
            package = None
        self.package = package

    def __call__(self):
        folder = self.get_cache_folder()
        json_cache_path = folder / self.JSON_CACHE_NAME
        session_cache_path = folder / self.SESSION_CACHE_NAME
        self._dump_reboot_info(json_cache_path, session_cache_path)
        if not self.package:
            raise ValueError(
                "Current folder is not within a plugin folder, so no reboot."
            )
        self.reboot()

    def get_cache_folder(self) -> Path:
        """Get the cache path.
        By reloading the `cache` file at the start of `.vimrc` / `init.lua`,
        """
        ui_enum = get_ui_enum()
        if ui_enum in {UIEnum.VSCODE, UIEnum.NVIM}:
            nvim_folder = Path(vim.eval("stdpath('cache')"))
            nvim_folder = to_filepath(nvim_folder)
            if not nvim_folder:
                nvim_folder.mkdir(parents=True)
            return nvim_folder
        elif ui_enum == UIEnum.VIM:
            if "XDG_CACHE_HOME" in os.environ:
                cache_dir = Path(os.environ["XDG_CACHE_HOME"])
            else:
                cache_dir = Path.home() / ".cache"
            vim_folder = cache_dir / "vim"
            if not vim_folder.exists():
                vim_folder.mkdir(parents=True)
            return vim_folder
        raise RuntimeError("Not Implmented.")

    def _dump_reboot_info(self, json_path, session_path):
        plugin_folder = self.package.root_folder.as_posix() if self.package else None
        data: dict[str, float | str] = {"time": time.time()}
        if plugin_folder:
            data["plugin_folder"] = plugin_folder
        json_path.write_text(json.dumps(data, indent=4))
        vim.command(f"mksession! {session_path.as_posix()}")

    def reboot(self):
        ui_enum = get_ui_enum()
        if ui_enum == ui_enum.VSCODE:
            from pytoy.ui.vscode.api import Api

            api = Api()
            api.action("vscode-neovim.restart")
            return
        rebooter = VimRebooter()

        rebooter()
        # if is_gui and sys.platform.startswith("win32"):
        #    if self.package:
        #        self.package.restart(with_vimrc=True, kill_myprocess=True)
        #    else:
        #        raise ValueError("Current folder is not within a plugin folder.")
        # else:
        #    vim.command("qall!")


@CommandManager.register(name="VimReboot")
class VimReboot:
    name = "VimReboot"

    def __call__(self):
        from pytoy.ui.vscode.api import Api

        executor = VimRebootExecutor()
        executor()

        if get_ui_enum() in {UIEnum.VIM, UIEnum.NVIM}:
            try:
                package = VimPluginPackage()
            except ValueError as e:
                print("Current folder is not within a plugin folder.", e)
            else:
                package.restart(with_vimrc=True, kill_myprocess=True)
        elif get_ui_enum() == UIEnum.VSCODE:
            try:
                package = VimPluginPackage()
                plugin_folder = package.root_folder.as_posix()
            except ValueError:
                plugin_folder = None
            path = Path(vim.eval("stdpath('cache')")) / "vscode_restarted.json"
            path = to_filepath(path)
            data = {"plugin_folder": plugin_folder, "time": time.time()}
            path.write_text(json.dumps(data, indent=4))

            api = Api()
            api.action("vscode-neovim.restart")


@CommandManager.register(name="DebugInfo")
def debug_info():
    import pytoy

    print(f"pytoy_location: `{pytoy.__file__}`")


class TimerTaskManagerDebug:
    taskname = "TimerTaskManagerDebug"

    @CommandManager.register(name="TimerTaskStart")
    @staticmethod
    def start():
        name = TimerTaskManagerDebug.taskname
        if TimerTask.is_registered(name):
            print("Already Registered.")
            return

        def _func():
            print("TimerTask Hello.")

        TimerTask.register(_func, interval=1000, name=name)

    @CommandManager.register(name="TimerTaskStop")
    @staticmethod
    def stop():
        name = TimerTaskManagerDebug.taskname
        if TimerTask.is_registered(name):
            TimerTask.deregister(name=name)
            print("Deregistered.")
        else:
            print("NotStarted")


@CommandManager.register(name="PytoyExecute")
def execute_pytoy(opts: OptsArgument):
    import vim
    import pytoy 
    from pytoy.ui.utils import to_filepath
    from pathlib import Path
    name = " ".join([elem.strip() for elem in opts.fargs])
    if not name:
        path = to_filepath(vim.current.buffer.name)
    else:
        path = to_filepath(name)

    match path.suffix:
        case ".py" | ".pyi":
            vim.command(f"py3file {path.as_posix()}")
        case ".vim":
            vim.command(f"source {path.as_posix()}")
        case _:
            raise ValueError("Cannot identify the apt execution for ``") 
