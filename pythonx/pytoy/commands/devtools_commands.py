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
            print("Current folder is not within a plugin folder.")
        else:
            package.restart(with_vimrc=True, kill_myprocess=True)


#class TimerTaskManagerDebug:
#    taskname = "TimerTaskManagerDebug"
#
#    @CommandManager.register(name="TimerTaskDebugStart")
#    def start(cls):
#        if TimerTaskManager.is_registered(cls.taskname):
#            print("Already Registered.")
#            return 
#        def _func():
#            print("TimerTask Hello.")
#        TimerTaskManager.register(_func, name=cls.taskname)
#
#    @CommandManager.register(name="TimerTaskDebugEnd")
#    def end(cls):
#        if TimerTaskManager.is_registered(cls.taskname):
#            print("Not Registered.")
#            return 
#        TimerTaskManager.deregister(cls.taskname)
#

taskname = "TimerTaskManagerDebug"
@CommandManager.register(name="TimerTaskDebugStart")
def start():
    if TimerTaskManager.is_registered(taskname):
        print("Already Registered.")
        return 
    def _func():
        print("TimerTask Hello.")
    TimerTaskManager.register(_func, name=taskname)


