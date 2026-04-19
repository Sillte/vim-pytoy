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


    def run(self, scope: Literal["func", "file", "folder", "workspace"], current_window: PytoyWindow | None = None):
        current_window = current_window or PytoyWindow.get_current()
        current_buffer = current_window.buffer

        path = current_buffer.file_path
        line = current_window.cursor.line + 1

        suffix = "--capture=no --quiet"
        match scope:
            case "func":
                command = to_func_command(path, line, suffix)
            case "file":
                command = f'pytest "{path}" {suffix}'
            case "folder":
                command = f'pytest "{path.parent}" {suffix}'
            case "workspace":
                workspace = PathResolver().to_workspace(path)
                if workspace is None:
                    raise ValueError(f"`{path=}` is not included in workspace.")
                command = f'pytest "{workspace}" {suffix}'

        def make_qf_records(content: str, cwd: Path) -> Sequence[QuickfixRecord]:
            rows = PytestDecipher(content).records
            return [QuickfixRecord.from_dict(row, cwd) for row in rows]

        hooks = get_default_hooks()
        hooks = ExecutionHooks.merge(hooks, QuickfixProfile(quickfix_creator=make_qf_records).execution_hooks)
        launch_profile = LaunchProfile(kind=self.kind, execution_hooks=hooks)
        CommandLauncher(launch_profile).run(command, stdout=self.stdout)

    def rerun(self) -> None:
        launcher = CommandLauncher(self.kind)
        launcher.rerun(stdout=self.stdout)