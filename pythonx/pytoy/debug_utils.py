"""Used for debugging and initialization.

Note
---------------------------------------------
Due to `reload` function, it is desirable to put this utility function
"""
import sys, os

def get_module_keys(root_folder=None):
    """Acquire the keys of `sys.module`
    whose modules resides under `root_folder`.
    """
    if root_folder is None:
        root_folder = os.path.dirname(os.path.abspath(__file__))
    elems = sys.modules
    targets = list()
    for key, mod in sys.modules.items():
        try:
            path = os.path.relpath(mod.__file__, root_folder)
        except (AttributeError, ValueError, TypeError): 
            pass
        else:
            if key != "__main__" and path[:2] != "..":
                targets.append(key)
    return targets

def reset_python(root_folder=None):
    """Delete the packages under root_folder.

    1. Delete modules under `root_folder` from `sys.modules`.
    2. import module of `root_folder / `__init__.py` as `root_folder`.name.
    """
    if root_folder is None:
        root_folder = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(root_folder, "__init__.py")
    if not os.path.exists(target_path):
        raise ValueError(f"Cannot found ``__init__.py`` for `{root_folder}`")

    keys = get_module_keys(root_folder)
    print("keys @ reload", keys)
    for key in keys:
        del sys.modules[key]

