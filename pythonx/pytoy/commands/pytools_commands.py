"""Python related commands."""

from typing import Sequence, assert_never
from pytoy.shared.ui.pytoy_buffer import make_buffer
from pytoy.shared.ui.pytoy_quickfix.models import QuickfixRecord

from pytoy.shared.command import App, Argument
from typing import Literal, Annotated

app = App()


@app.command("Pytest")
def pytest_command(command_type: Annotated[Literal["func", "file", "all"], Argument()] = "func"):

    from pytoy.job_execution.command_executor import QuickfixCommandExecutor
    from pytoy.job_execution.command_executor import QuickfixCommandRequest
    from pytoy.job_execution.command_executor import ExecutionRequest
    from pytoy.job_execution.command_executor import BufferRequest
    from pytoy.shared.ui import PytoyBuffer, PytoyWindow
    from pytoy.tools.pytest.utils import to_func_command, PytestDecipher
    from pytoy import TERM_STDOUT

    current_window = PytoyWindow.get_current()
    current_buffer: PytoyBuffer = current_window.buffer
    path = current_buffer.file_path
    cwd = path.parent
    line_1based = current_window.cursor.line + 1

    pytoy_buffer = make_buffer(TERM_STDOUT, "vertical")

    def build_command(command_type: Literal["func", "file", "all"], path, line, suffix):
        match command_type:
            case "func":
                return to_func_command(path, line, suffix)
            case "file":
                return f'pytest "{path}" {suffix}'
            case "all":
                return f"pytest {suffix}"
            case _:
                assert_never(command_type)

    suffix = "--capture=no --quiet"
    command = build_command(command_type, path, line_1based, suffix)

    def make_qf_records(content: str) -> Sequence[QuickfixRecord]:
        rows = PytestDecipher(content).records
        return [QuickfixRecord.from_dict(row, cwd) for row in rows]

    executor = QuickfixCommandExecutor(BufferRequest(stdout=pytoy_buffer))
    execution = ExecutionRequest(command=command, cwd=cwd)
    request = QuickfixCommandRequest(execution=execution, creator=make_qf_records)
    executor.execute(request)


@app.command(name="Mypy")
def mypy_command(target: Annotated[Literal["workspace", "current"] | str | None, Argument()] = None):
    from pytoy.job_execution.command_executor import QuickfixCommandExecutor, QuickfixCommandRequest, ExecutionRequest
    from pytoy.job_execution.command_executor import BufferRequest
    from pytoy import TERM_STDOUT
    from pytoy.commands.utils import workspace_func
    from pytoy.shared.ui import PytoyBuffer
    
    current_path = PytoyBuffer.get_current().file_path

    if target == "workspace":
        path = workspace_func()
    elif target == "current":
        path = current_path
    else:
        path = workspace_func() or current_path

    pytoy_buffer = make_buffer(TERM_STDOUT, "vertical")
    command = f'mypy --show-traceback --show-column-numbers "{path}"'
    executor = QuickfixCommandExecutor(buffer_request=BufferRequest(stdout=pytoy_buffer))
    execution = ExecutionRequest(command=command, cwd=current_path.parent)

    quickfix_regex = r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+):(?P<_type>(.+)):(?P<text>(.+))"
    request = QuickfixCommandRequest(execution=execution, creator=quickfix_regex)
    executor.execute(request)


@app.command(name="CSpell")
def cspell_command():
    from pathlib import Path
    from pytoy import TERM_STDOUT
    from pytoy.tools.cspell import CSpellOneFileChecker
    from pytoy.shared.ui.pytoy_quickfix import PytoyQuickfix, handle_records, to_quickfix_creator
    from pytoy.shared.ui import PytoyBuffer

    path = PytoyBuffer.get_current().file_path

    if Path(path).suffix == ".py":
        checker = CSpellOneFileChecker(only_python_string=True)
    else:
        checker = CSpellOneFileChecker(only_python_string=False)
    output = checker(path)
    regex = r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+).*\((?P<text>(.+))\)"
    maker = to_quickfix_creator(regex, cwd=path.parent)
    records = maker(output)
    handle_records(PytoyQuickfix(), records)


@app.command(name="RuffCheck")
def ruff_check(
    target: Annotated[Literal["workspace", "current"] | None | str, Argument()] = None,
    fix: bool = True,
    format: bool = False,
    unsafe: bool = False,
):

    from pytoy import TERM_STDOUT
    from pytoy.commands.utils import workspace_func
    from pytoy.contexts.core import GlobalCoreContext

    from pytoy.job_execution.command_executor import QuickfixCommandExecutor, QuickfixCommandRequest, ExecutionRequest
    from pytoy.job_execution.command_executor import BufferRequest
    from pathlib import Path
    from pytoy.shared.ui import PytoyBuffer

    current_path = PytoyBuffer.get_current().file_path
    cwd = current_path.parent
    env_manager = GlobalCoreContext.get().environment_manager
    execution_env = env_manager.solve_preference(cwd, preference=None)
    pytoy_buffer = make_buffer(TERM_STDOUT, "vertical")

    def _format(path: str | Path) -> None:
        import subprocess

        command = f'ruff format "{path}"'
        command = execution_env.command_wrapper(command)

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            text=True,
        )
        pytoy_buffer.init_buffer(result.stdout)

    if target == "workspace":
        path = workspace_func()
    elif target == "current":
        path = current_path
    elif isinstance(target, str):
        path = Path(target)
    elif target is None:
        path = current_path or workspace_func()
    else:
        path = current_path

    if path is None:
        raise ValueError("Given input is not valid.")

    if format:
        _format(path)

    buffer_request = BufferRequest(stdout=pytoy_buffer)
    pytoy_buffer.init_buffer()
    executor = QuickfixCommandExecutor(buffer_request)
    option_str = ""
    if fix is True:
        option_str += " --fix "
    if unsafe is True:
        option_str += " --unsafe-fixes "

    command = f'ruff check "{path}" --output-format=concise {option_str}'
    execution = ExecutionRequest(
        command=command, cwd=current_path.parent, command_wrapper=execution_env.command_wrapper
    )
    qf_creator = r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+):(?P<text>(.+))"

    request = QuickfixCommandRequest(execution=execution, creator=qf_creator)
    executor.execute(request, init_buffer=False)


if __name__ == "__main__":
    pass
