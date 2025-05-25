from pytoy.command import CommandManager
from pytoy.devtools.vimplugin_package import VimPluginPackage

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

