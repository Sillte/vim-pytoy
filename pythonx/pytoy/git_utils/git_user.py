import subprocess
import re
from typing import List, Callable, Any
from subprocess import PIPE
from pathlib import Path


class GitUser:
    """Perusing git related information.

    Args:
        cwd: current_directory.
    """

    def __init__(self, cwd: None | Path = None):
        if cwd is None:
            cwd = Path.cwd().absolute()
        self.cwd = Path(cwd)
        if not self.cwd.exists():
            raise ValueError("Given `cwd` is not existent.")
        self.toplevel  # Confirmation of folder.

    @property
    def toplevel(self) -> Path:
        """Return the parent of `.git` folder."""
        ret = self._run("git rev-parse --show-toplevel")
        if ret.returncode != 0:
            raise ValueError("This is not `.git` folder.")
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
        ret = self._run("git ls-files", cwd=self.toplevel)
        paths = []
        paths = [Path(line.strip()).absolute() for line in ret.stdout.split("\n")]
        return paths

    def _run(self, cmd, **kwargs):
        default = dict()
        default["text"] = True
        default["cwd"] = self.cwd
        default["stdout"] = PIPE
        default["shell"] = True  # To prevent flickering.
        default.update(kwargs)
        return subprocess.run(cmd, **default)


def get_git_info(local_filepath) -> dict[str, str]:
    """Return the information regarding git."""
    local_filepath = Path(local_filepath)
    cwd = str(local_filepath.parent)

    def _run_git(args):
        return subprocess.check_output(["git"] + args, cwd=cwd, shell=True).decode().strip()

    result = dict()
    result["rootpath"] = _run_git(["rev-parse", "--show-toplevel"])
    result["filepath"] = str(local_filepath)
    result["relpath"] = str(
        local_filepath.resolve().relative_to(Path(result["rootpath"])).as_posix()
    )
    result["branch"] = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    result["remote"] = _run_git(["remote", "get-url", "origin"])
    return result


REMOTE_TO_MAKER: dict[str, Callable[[dict[str, str], dict[str, str]], str]] = dict()


def _to_github_address(info: dict[str, str], options: dict[str, Any]):
    remote = info["remote"]
    branch = info["branch"]
    relpath = info["relpath"]
    remote = remote.replace(".git", "").replace(
        "git@github.com:", "https://github.com/"
    )
    path = f"{remote}/blob/{branch}/{relpath}"
    if "line" in options:
        path += f"#L{options['line']}"
    return path


def _to_azure_address(info: dict[str, str], options: dict[str, Any]):
    remote = info["remote"]
    branch = info["branch"]
    relpath = info["relpath"].strip("/")
    if remote.startswith("https://dev.azure.com/"):
        m = re.match(r"https://dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+)", remote)
        if not m:
            raise ValueError(f"Invalid Azure Address {remote=}")
    elif remote.startswith("git@ssh.dev.azure.com:"):
        m = re.match(r"git@ssh\.dev\.azure\.com:v3/([^/]+)/([^/]+)/([^/]+)", remote)
        if not m:
            raise ValueError("Invalid Azure Address {remote=}")
    else:
        raise ValueError("Invalid Azure Address {remote=}")
    org, project, repo = m.groups()

    url = (
        f"https://dev.azure.com/{org}/{project}/_git/{repo}"
        f"?path=/{relpath}&version=GB{branch}"
    )

    queries = dict()
    if "line" in options:
        queries["line"] = options["line"]
    if queries:
        a_param: str = "&".join([f"{key}={value}" for key, value in queries.items()])
        url = f"{url}&{a_param}"
    return url


REMOTE_TO_MAKER["github.com"] = _to_github_address
REMOTE_TO_MAKER["dev.azure.com"] = _to_azure_address

def get_remote_link(local_filepath: str | Path, line: int | None = None):
    info = get_git_info(local_filepath)
    options = dict()
    if line is not None:
        options["line"] = line

    for key, func in REMOTE_TO_MAKER.items():
        if key in info["remote"]:
            return func(info, options)
    raise ValueError(
        "Cannot resolve remote adress{info['remote']=}\n"
        "For workaround, please consider to add `REMOTE_TO_MAKER`.",
    )


if __name__ == "__main__":
    from pathlib import Path

    target_folder = Path().cwd()
    user = GitUser(cwd=target_folder)
    print(user.toplevel)
    print(user.branch)
    print(user.initial_commit)
    print(user.target_files)
    import subprocess

    from pathlib import Path

    print(get_remote_link(__file__, 10))
