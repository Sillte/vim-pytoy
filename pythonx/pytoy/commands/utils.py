# Theare are utility functions to define `commands`.    

#  When we define the commands, there are two cases. 
# 1. `pytoy.command.OptsArgument`
# 2. `Annotation of `dict`, `str` `list`.
#
# This module mainly considers an utility function which is written with the naive types of python.  
#

from typing import Callable, Sequence, Mapping

type F_ARGS = list[str]
type OVERRIDE_FUNC = Callable[[], str | None]
type OVERRIDE_MAP  = Mapping[str, OVERRIDE_FUNC]

def override(fargs: Sequence[str], funcs: OVERRIDE_MAP) -> F_ARGS:
    """Override the a part of `f_args`, based on functions.
    """
    items: list[str | None] = list(fargs)
    for key, func in funcs.items():
        if key in items:
            index = items.index(key)
            result = func()
            items[index] = result or None  
    return [item for item in items if item is not None] 

def fallback_argument(fargs: Sequence[str], target: str) -> F_ARGS:
    """If there is no argument, `target is inserted."""
    items = list(fargs)
    arguments = [elem for elem in items if not elem.startswith("-")]
    if not arguments:
        items.insert(0, target)
    return items


def workspace_func() -> str | None:
    from pytoy.lib_tools.environment_manager import EnvironmentManager
    from pytoy.lib_tools.utils import get_current_directory
    current_folder = get_current_directory()
    workspace = EnvironmentManager().get_workspace(current_folder, preference="auto")
    if not workspace:
        print("Cannot obtain `workspace`.")
        return None
    return str(workspace)

WORKSPACE_OVERRIDE_MAP = {"workspace": workspace_func}
