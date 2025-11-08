from pytoy.command import CommandManager


@CommandManager.register(name="UVToggle")
class UvToggle:
    """Switch the UVMode."""

    def __call__(self):
        from pytoy.lib_tools.environment_manager import EnvironmentManager

        manager = EnvironmentManager()
        manager.toggle_uv_mode()
