# Theare are utility functions to define `commands`.    


def workspace_func() -> str | None:
    from pytoy.job_execution.environment_manager import EnvironmentManager
    from pytoy.job_execution.utils import get_current_directory
    current_folder = get_current_directory()
    workspace = EnvironmentManager().get_workspace(current_folder, preference="auto")
    if not workspace:
        print("Cannot obtain `workspace`.")
        return None
    return str(workspace)

WORKSPACE_OVERRIDE_MAP = {"workspace": workspace_func}
