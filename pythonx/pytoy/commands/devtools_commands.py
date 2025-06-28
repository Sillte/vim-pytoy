from pathlib import Path
import time
import json
import vim
from pytoy.command import CommandManager
from pytoy.devtools.vimplugin_package import VimPluginPackage
from pytoy.infra.timertask import TimerTask
from pytoy.ui import get_ui_enum, UIEnum
from pytoy.ui.vscode.api import Api

@CommandManager.register(name="VimReboot")
class VimReboot:
    name = "VimReboot"
    def __call__(self):
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
            except ValueError as e:
                plugin_folder = None
            path = Path(vim.eval("stdpath('cache')")) / "vscode_restarted.json"
            data = {"plugin_folder": plugin_folder, 
                    "time": time.time()}
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


#CommandManager.register(name="DEBUG")(TimerTaskManagerDebug.start)


#taskname = "TimerTaskManagerDebug"
#@CommandManager.register(name="TimerTaskDebugStart")
#def start():
#    if TimerTask.is_registered(taskname):
#        print("Already Registered.")
#        return 
#    def _func():
#        print("TimerTask Hello.")
#    TimerTask.register(_func, name=taskname)
#

