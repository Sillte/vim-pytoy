import json
import os
import time
from pathlib import Path
from typing import Annotated, Literal

from pytoy.devtools.vim_rebooter import VimRebooter
from pytoy.devtools.vimplugin_package import VimPluginPackage
from pytoy.shared.command import App, Argument
from pytoy.shared.lib.backend import BackendEnum, get_backend_enum
from pytoy.shared.timertask import TimerTask


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
            raise ValueError("Current folder is not within a plugin folder, so no reboot.")
        self.reboot()

    def get_cache_folder(self) -> Path:
        """Get the cache path.
        By reloading the `cache` file at the start of `.vimrc` / `init.lua`,
        """
        backend_enum = get_backend_enum()
        if backend_enum in {BackendEnum.VSCODE, BackendEnum.NVIM}:
            import vim

            nvim_folder = Path(vim.eval("stdpath('cache')"))
            if not nvim_folder:
                nvim_folder.mkdir(parents=True)
            return nvim_folder
        elif backend_enum == BackendEnum.VIM:
            import vim

            if "XDG_CACHE_HOME" in os.environ:
                cache_dir = Path(os.environ["XDG_CACHE_HOME"])
            else:
                cache_dir = Path.home() / ".cache"
            vim_folder = cache_dir / "vim"
            if not vim_folder.exists():
                vim_folder.mkdir(parents=True)
            return vim_folder
        else:
            dummy_folder = Path.home() / ".cache" / "dummy_pytoy"
            dummy_folder.mkdir(parents=True, exist_ok=True)
            return dummy_folder
        raise RuntimeError("Not Implmented.")

    def _dump_reboot_info(self, json_path, session_path):
        import vim

        plugin_folder = self.package.root_folder.as_posix() if self.package else None
        data: dict[str, float | str] = {"time": time.time()}
        if plugin_folder:
            data["plugin_folder"] = plugin_folder
        json_path.write_text(json.dumps(data, indent=4))
        vim.command(f"mksession! {session_path.as_posix()}")

    def reboot(self):
        backend_enum = get_backend_enum()
        if backend_enum == BackendEnum.VSCODE:
            from pytoy.shared.ui.vscode.api import Api

            api = Api()
            api.action("vscode-neovim.restart")
            return
        elif backend_enum in {BackendEnum.VIM, BackendEnum.NVIM}:
            rebooter = VimRebooter()
            rebooter()
        else:
            print("Reboot is not supported for `Dummy`.")


app = App()


@app.command(name="VimReboot")
def vim_reboot():
    executor = VimRebootExecutor()
    executor()
    backend_enum = get_backend_enum()

    if backend_enum in {BackendEnum.VIM, BackendEnum.NVIM}:
        try:
            package = VimPluginPackage()
        except ValueError as e:
            print("Current folder is not within a plugin folder.", e)
        else:
            package.restart(with_vimrc=True, kill_myprocess=True)
    elif backend_enum == BackendEnum.VSCODE:
        try:
            package = VimPluginPackage()
            plugin_folder = package.root_folder.as_posix()
        except ValueError:
            plugin_folder = None
        import vim

        path = Path(vim.eval("stdpath('cache')")) / "vscode_restarted.json"
        data = {"plugin_folder": plugin_folder, "time": time.time()}
        path.write_text(json.dumps(data, indent=4))
        from pytoy.shared.ui.vscode.api import Api

        api = Api()
        api.action("vscode-neovim.restart")
    else:
        print("Reboot is not supported for `Dummy`.")


@app.command(name="DebugInfo")
def debug_info():
    import pytoy

    print(f"pytoy_location: `{pytoy.__file__}`")


DEBUG_TIMER_TASK_NAME = "TimerTaskManagerDebug"


@app.command("TimerTaskStart")
def timer_task_start():
    name = DEBUG_TIMER_TASK_NAME
    if TimerTask.is_registered(name):
        print("Already Registered.")
        return

    def _func():
        print("TimerTask Hello.")

    TimerTask.register(_func, interval=1000, name=name)


@app.command("TimerTaskStop")
def timer_task_stop():
    name = DEBUG_TIMER_TASK_NAME
    if TimerTask.is_registered(name):
        TimerTask.deregister(name=name)
        print("Deregistered.")
    else:
        print("NotStarted")


@app.command("PytoyExecute")
def pytoy_execute(input_path: Annotated[str | None, Argument()] = None):
    from pathlib import Path

    import vim

    from pytoy.shared.ui import PytoyBuffer

    if not input_path:
        path = PytoyBuffer.get_current().file_path
    else:
        path = Path(input_path)

    match path.suffix:
        case ".py" | ".pyi":
            vim.command(f"py3file {path.as_posix()}")
        case ".vim":
            vim.command(f"source {path.as_posix()}")
        case _:
            raise ValueError("Cannot identify the apt execution for ``")


@app.command(name="PytoyLog")
def pytoy_log(location: Annotated[Literal["local", "global"] | None, Argument()] = None):
    import logging
    from pathlib import Path

    from pytoy.contexts.core import GlobalCoreContext
    from pytoy.shared.pytoy_configuration import PytoyConfiguration
    from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
    from pytoy.shared.ui.pytoy_window import PytoyWindow

    logger = PytoyConfiguration().get_logger(location="global", level=logging.INFO)
    logger.info("Opening a Log file.")

    c_buffer = PytoyBuffer.get_current()
    if c_buffer.is_file:
        pivot_folder = c_buffer.file_path
    else:
        pivot_folder = Path(".")
    workspace = GlobalCoreContext().get().environment_manager.find_workspace(pivot_folder)
    workspace = workspace if workspace else pivot_folder
    config = PytoyConfiguration(workspace)

    target_path = config.get_latest_log_path(location)
    if target_path is None:
        raise ValueError("Cannot find the apt log folder.")
    PytoyWindow.open(target_path, "vertical")
