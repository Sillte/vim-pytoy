from pytoy.command_utils import CommandManager


@CommandManager.register(name="UVToggle")
class UvToggle:
    """Switch the UVMode.
    """
    def __call__(self, *args):
        from pytoy.environment_manager import EnvironmentManager
        manager = EnvironmentManager()
        manager.toggle_uv_mode()
