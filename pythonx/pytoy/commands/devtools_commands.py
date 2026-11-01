from typing import Annotated, Literal

from pytoy.devtools import PluginRebooter
from pytoy.shared.command import App, Argument
from pytoy.shared.timertask import TimerTask

app = App()


@app.command(name="VimReboot")
def vim_reboot():
    PluginRebooter().restart()


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
