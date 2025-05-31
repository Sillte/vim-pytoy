from pytoy.command import CommandManager
from pytoy.devtools.vimplugin_package import VimPluginPackage
from pytoy.timertask_manager import TimerTaskManager

@CommandManager.register(name="VimReboot")
class VimReboot:
    name = "VimReboot"
    def __call__(self):
        try:
            package = VimPluginPackage()
        except ValueError as e:
            print("Current folder is not within a plugin folder.", e)
        else:
            package.restart(with_vimrc=True, kill_myprocess=True)


class TimerTaskManagerDebug:
    taskname = "TimerTaskManagerDebug"

    @CommandManager.register(name="TimerTaskStart")
    @staticmethod
    def start():
        name = TimerTaskManagerDebug.taskname
        if TimerTaskManager.is_registered(name):
            print("Already Registered.")
            return 
        def _func():
            print("TimerTask Hello.")
        TimerTaskManager.register(_func, interval=1000, name=name)

    @CommandManager.register(name="TimerTaskStop")
    @staticmethod
    def stop():
        name = TimerTaskManagerDebug.taskname
        if TimerTaskManager.is_registered(name):
            TimerTaskManager.deregister(name=name)
            print("Deregistered.")
        else:
            print("NotStarted")


#CommandManager.register(name="DEBUG")(TimerTaskManagerDebug.start)


#taskname = "TimerTaskManagerDebug"
#@CommandManager.register(name="TimerTaskDebugStart")
#def start():
#    if TimerTaskManager.is_registered(taskname):
#        print("Already Registered.")
#        return 
#    def _func():
#        print("TimerTask Hello.")
#    TimerTaskManager.register(_func, name=taskname)
#

