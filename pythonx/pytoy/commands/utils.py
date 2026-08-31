# Theare are utility functions to define `commands`.


def workspace_func() -> str | None:
    from pytoy.tool_execution.environment_manager.current import get_current_directory
    from pytoy.tool_execution.environment_manager.manager import EnvironmentManager

    current_folder = get_current_directory()
    workspace = EnvironmentManager().find_workspace(current_folder, preference="auto")
    if not workspace:
        print("Cannot obtain `workspace`.")
        return None
    return str(workspace)


WORKSPACE_OVERRIDE_MAP = {"workspace": workspace_func}
