"""Utility functions as for virtual environments.

"""

import sys
import subprocess
from pathlib import Path
from typing import List, Optional

try:
    import vim
except ImportError:
    pass


def search(
    root_folder: Optional[Path] = None, n_depth: int = 1, name: Optional[str] = None
) -> List[Path]:
    """Search the `virtualenv` folders  around `root_folder`.

    Args:
        name: If specified, only `name` environment is gathered.

    Return:
        List of `virtualenv` folders, which resides proximities of `n_depth`.
        * The index of `Path` is as smaller as it is closer to `root_folder`. 
        * The index of `Path` of descendant is smaller  when `distance` equals.  
    """

    def _is_virtualenv(folder):
        # Imagine Windows.
        if (folder / "Scripts/activate").exists():
            if (folder / "Lib").exists():
                return True
        # Imagine Linux.
        if (folder / "bin/activate").exists():
            return True
        return False

    if root_folder is None:
        root_folder = Path(".")
    else:
        root_folder = Path(root_folder)
    root_folder = root_folder.absolute()

    results = list()
    visited = set()
    queue = [(root_folder, 0)]  # (folder, depth)
    while queue:
        current, depth = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        if _is_virtualenv(current):
            if name:
                if current.name == name:
                    results.append(current)
            else:
                results.append(current)

        try:
            for path in filter(lambda p: p.is_dir(), current.iterdir()):
                if depth < n_depth:
                    queue.append((path, depth + 1))
        except PermissionError:
            pass
        queue.append((current.parent, depth + 1))
    return results


def pick(name, root_folder: Optional[Path] = None, n_depth: int = 1) -> Path:
    """Pick the `virtualenv`

    Raise:
        ValueError: If `virtualenv` is not found.

    Note
    ----
    This is not efficiency in terms of searching all the folders first.
    """
    folders = search(root_folder, n_depth, name=name)
    if folders:
        return folders[0]
    raise ValueError(f"Cannot find `{name}` virtualenv")


class VenvManager:
    """Handles `virtual environments` for 
    """
    __cache = None

    try:
        import vim
    except ImportError:
        _is_vim = False
    else:
        _is_vim = True

    def __new__(cls):
        if  cls.__cache is None:
            self = object.__new__(cls)
            cls.__cache = self
            self._init()
        else:
            self = cls.__cache
        return self
    
    def _init(self):
        self.name = None
        self.path = None
        self.prev_vimpath = None

    @property
    def is_activated(self):
        return self.name is not None

    @property
    def envinfo(self):
        if not self.is_activated:
            return None
        else:
            return (self.name, str(self.path))

    def activate(self, name=None, path=None, root=None, n_depth=1):
        """Activate `name` virtualenv with `path`.
        """
        if name is None:
            if path is None:
                paths = search(root_folder=root, n_depth=n_depth)
                if paths:
                    path = paths[0]
                    name = path.name
                else:
                    raise ValueError(f"`name` is not given, and cannot estimate.")
            else:
                name = Path(path).name
        if path:
            path = Path(path)
        else:
            path = pick(name, root_folder=root, n_depth=n_depth)
        if not path.exists():
            raise ValueError(f"`{path}` does not exist.")

        if self.is_activated:
            self.deactivate()
        self.path = path
        self.name = name

        if self._is_vim:
            self.prev_vimpath = vim.eval("$PATH")

        activate(path)


    def deactivate(self):
        if not self.is_activated:
            return 

        if self._is_vim:
            vim.command(f"let $PATH='{self.prev_vimpath}'")
        
        self._init()

        deactivate()

    def term_start(self, external=False):
        """Open Terminal.
        The behavior is different when `import vim` is valid or not.
        """
        if not self.is_activated:
            raise ValueError("Virtual Environment is not activated.")

        if sys.platform != "win32":
            raise NotImplementedError("Not yet implemented for `{sys.platform}`.")

        bat_path = self.path / "Scripts" / "activate.bat"

        try:
            import vim
        except ImportError:
            external = True

        if external: 
            subprocess.run(["start", str(bat_path)], shell=True)
        else:
            commands = ["start", bat_path]
            options = {"term_name" : self.name}
            vim.command(f":call term_start({command}, {options})")

# To omit the necessity of exclusive processings.
VenvManager()


"""
* `active_content` / `deactivate` / `activate`
    Refer to `https://github.com/jmcantrell/vim-virtualenv/blob/master/autoload/pyvenv.py`. 
"""

import os, sys

prev_syspath = None

activate_content = """
try:
    __file__
except NameError:
    raise AssertionError(
        "You must run this like execfile('path/to/activate_this.py', dict(__file__='path/to/activate_this.py'))")
import sys
import os
old_os_path = os.environ['PATH']
os.environ['PATH'] = os.path.dirname(os.path.abspath(__file__)) + os.pathsep + old_os_path
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if sys.platform == 'win32':
    site_packages = os.path.join(base, 'Lib', 'site-packages')
else:
    version = '%s.%s' % (sys.version_info.major, sys.version_info.minor)
    site_packages = os.path.join(base, 'lib', 'python%s' % version, 'site-packages')
prev_sys_path = list(sys.path)
import site
site.addsitedir(site_packages)
sys.real_prefix = sys.prefix
sys.prefix = base
# Move the added items to the front of the path:
new_sys_path = []
for item in list(sys.path):
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)
sys.path[:0] = new_sys_path
"""

def activate(env):
    global prev_syspath
    prev_syspath = list(sys.path)
    activate = os.path.join(env, (sys.platform == 'win32') and 'Scripts' or 'bin', 'activate_this.py')
    try:
        fo = open(activate)
        f = fo.read()
        fo.close()
    except:
        f = activate_content

    code = compile(f, activate, 'exec')
    exec(code, dict(__file__=activate))


def deactivate():
    global prev_syspath
    try:
        sys.path[:] = prev_syspath
        prev_syspath = None
    except:
        pass

if __name__ == "__main__":
    vm = VenvManager()
    vm.activate()
    vm.term_start()
    #print(pick("black", n_depth=3))
