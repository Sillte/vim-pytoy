from pathlib import Path
import time
import os
import json
import vim
from logging.handlers import RotatingFileHandler
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


@CommandManager.register(name="PytoyLog")
class PytoyOpenLog:
    def __call__(self, opts: OptsArgument) -> None:
        from pytoy.contexts.core import GlobalCoreContext
        from pytoy.infra.pytoy_configuration import PytoyConfiguration
        from pytoy.ui.pytoy_buffer import PytoyBuffer
        from pytoy.ui.pytoy_window import PytoyWindow
        from pathlib import Path
        import logging
        logger = PytoyConfiguration().get_logger(location="global", level=logging.INFO)
        logger.info("Opening a Log file.")

        c_buffer = PytoyBuffer.get_current()
        if c_buffer.is_file:
            pivot_folder = c_buffer.path
        else:
            pivot_folder = Path(".")
            raise ValueError("Current folder should be `file`. ") 
        workspace = GlobalCoreContext().get().environment_manager.get_workspace(pivot_folder)
        workspace = workspace if workspace else pivot_folder
        config = PytoyConfiguration(workspace, local_config_type=None)
        location = None
        if opts.fargs:
            if opts.fargs[0] == "local":
                location = "local"
            elif opts.fargs[0] == "global":
                location = "global"
                
        if location is not None: 
            target_path = self._logger_to_latest_log(config.get_logger(location))
        else:
            if config.is_logger_exist("local"):
                logger = config.get_logger("local")
                target_path = self._logger_to_latest_log(logger)
            else:
                target_path = self._logger_to_latest_log(config.get_logger("global"))
        if target_path is None:
            raise ValueError("Cannot find the apt log folder.")
        PytoyWindow.open(target_path, "vertical")
            
    def _logger_to_latest_log(self, logger) -> None | Path:
        log_files = []
        for h in logger.handlers:
            if isinstance(h, RotatingFileHandler):
                folder = Path(h.baseFilename).parent
                pattern = Path(h.baseFilename).name + "*"
                log_files.extend(folder.glob(pattern))
        if not log_files:
            return None
        return sorted(log_files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
            
