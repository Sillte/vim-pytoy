import subprocess
from typing import List, Dict
from subprocess import PIPE 
from pathlib import Path


class GitUser: 
    """Perusing git related information.
    
    Args:
        cwd: current_directory.
    """ 
    def __init__(self, cwd:Path=None):
        if cwd is None:
            cwd = Path.cwd().absolute()
        self.cwd = Path(cwd)
        if not self.cwd.exists():
            raise ValueError("Given `cwd` is not existent.") 
        self.toplevel  # Confirmation of folder.

    @property
    def toplevel(self) -> Path:
        """Return the parent of `.git` folder.
        """
        ret = self._run("git rev-parse --show-toplevel")
        if ret.returncode != 0:
            raise ValueError(f"This is not `.git` folder.")
        return Path(ret.stdout.strip())

    @property
    def branch(self) -> str:
        ret = self._run("git rev-parse --abbrev-ref HEAD")
        return ret.stdout.strip()

    @property
    def initial_commit(self) -> str:
        ret = self._run("git rev-list --max-parents=0 HEAD")
        return ret.stdout.strip()

    @property
    def target_files(self) -> List[Path]:
        initial_commit = self.initial_commit
        ret = self._run("git ls-files", cwd=self.toplevel)
        paths = []
        paths = [Path(line.strip()).absolute() for line in ret.stdout.split("\n")]
        return paths

    def _run(self, cmd, **kwargs):
        default = dict()
        default["text"] = True
        default["cwd"] = self.cwd
        default["stdout"] = PIPE
        default.update(kwargs)
        return subprocess.run(cmd, **default)


if __name__ == "__main__":
    target_folder = r"C:\Library\myvimrc"
    user = GitUser(cwd=target_folder)
    print(user.toplevel)
    print(user.branch)
    print(user.initial_commit)
    print(user.target_files)
