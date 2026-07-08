from configparser import ConfigParser
from pytoy import TERM_STDOUT
from pytoy.job_execution.command_executor.launcher import CommandLauncher, LaunchProfile, get_default_hooks
from pytoy.job_execution.command_executor import ExecutionHooks
from pytoy.job_execution.command_executor.launcher.quickfix import QuickfixProfile
from pytoy.shared.ui import PytoyBuffer, PytoyWindow, QuickfixRecord
from pytoy.shared.ui.pytoy_buffer import make_buffer
from pytoy.tools.pytest.utils import PytestDecipher, to_func_command
from pytoy.tools.python.path_resolver import PathResolver


from pathlib import Path
from typing import Literal, Sequence


class PytestRunner:
    def __init__(self) -> None:
        pass

    @property
    def kind(self):
        return "PytestRunner"

    @property
    def stdout(self) -> PytoyBuffer:
        return make_buffer(TERM_STDOUT, "vertical")


    def run(self, scope: Literal["func", "file", "folder", "workspace"], current_window: PytoyWindow | None = None, cwd: str | Path | None = None):
        current_window = current_window or PytoyWindow.get_current()
        current_buffer = current_window.buffer

        path = current_buffer.file_path
        line = current_window.cursor.line + 1

        suffix = "--capture=no --quiet"
        match scope:
            case "func":
                command = to_func_command(path, line, suffix)
                cwd = self._decide_pytest_cwd(path, cwd=cwd)
            case "file":
                command = f'pytest "{path}" {suffix}'
                cwd = self._decide_pytest_cwd(path, cwd=cwd)
            case "folder":
                command = f'pytest "{path.parent}" {suffix}'
                cwd = self._decide_pytest_cwd(path.parent, cwd=cwd)
            case "workspace":
                workspace = PathResolver().to_workspace(path)
                if workspace is None:
                    raise ValueError(f"`{path=}` is not included in workspace.")
                command = f'pytest "{workspace}" {suffix}'
                cwd = self._decide_pytest_cwd(workspace, cwd=cwd)

        def make_qf_records(content: str, cwd: Path) -> Sequence[QuickfixRecord]:
            rows = PytestDecipher(content).records
            return [QuickfixRecord.from_dict(row, cwd) for row in rows]

        hooks = get_default_hooks()
        hooks = ExecutionHooks.merge(hooks, QuickfixProfile(quickfix_creator=make_qf_records).execution_hooks)
        launch_profile = LaunchProfile(kind=self.kind, execution_hooks=hooks)
        CommandLauncher(launch_profile).run(command, stdout=self.stdout, stderr=self.stdout, cwd=cwd)

    def rerun(self) -> None:
        launcher = CommandLauncher(self.kind)
        launcher.rerun(stdout=self.stdout)
        

    def _decide_pytest_cwd(self, target_path: Path, *,  cwd: Path | str | None) -> Path:
        if cwd is not None:
            return Path(cwd).resolve()

        target_path = Path(target_path).resolve()
        for parent in [target_path] + list(target_path.parents):
            if _has_pytest_config(parent):
                return parent
        project = PathResolver().to_project(target_path)
        if project is not None:
            return project
        return target_path if target_path.is_dir() else target_path.parent

            

def _has_pytest_config(folder: Path) -> bool:
    for name in ["pytest.toml", "pytest.ini"]:
        if (folder / name).exists():
            return True

    for name, section in [("tox.ini", "pytest"), ("setup.cfg", "tool:pytest")]:
        tox_ini = folder / name
        if tox_ini.exists():
            if _has_ini_section(tox_ini, section):
                return True

    pyproject = folder / "pyproject.toml"
    if pyproject.exists():
        return _has_pyproject_pytest(pyproject)

    return False

def _has_ini_section(path: Path, section: str) -> bool:
    parser = ConfigParser()
    try:
        parser.read(path, encoding="utf-8")
    except Exception:
        return False
    return parser.has_section(section)


def _has_pyproject_pytest(pyproject: Path) -> bool:
    import tomllib
    try:
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return False
    return isinstance(
        data.get("tool", {}).get("pytest"),
        dict,
    )