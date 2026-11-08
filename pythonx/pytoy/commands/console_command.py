from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

from pytoy import TERM_STDERR, TERM_STDOUT
from pytoy.shared.command import App, Argument, Group, Option, RangeParam

if TYPE_CHECKING:
    from pytoy.shared.ui.pytoy_buffer import PytoyBuffer

app = App()

_TERMINAL_BUFFER_NAMES = frozenset({"__TERMINAL__", "__SHELL__", "__IPYTYON__", TERM_STDOUT, TERM_STDERR})


@app.command("Console")
def console(
    driver: Annotated[str | None, Option()] = None,
    buffer: Annotated[str, Option()] = "__TERMINAL__",
    cwd: Annotated[str | Path | None, Option()] = None,
) -> None:
    from pytoy.tools.console import ConsoleRunner

    ConsoleRunner().open(buffer, driver, cwd=cwd)


@app.command("ConsoleRun")
def console_run(
    cmd: Annotated[str, Argument()],
    driver: Annotated[str | None, Option()] = None,
    buffer: Annotated[str, Option()] = "__TERMINAL__",
    cwd: Annotated[str | Path | None, Option()] = None,
) -> None:
    from pytoy.tools.console import ConsoleRunner

    ConsoleRunner().run(cmd, buffer, driver, cwd=cwd)


@app.command("ConsoleSend")
def console_send(
    driver: Annotated[str | None, Option()] = None,
    buffer: Annotated[str, Option()] = "__TERMINAL__",
    cwd: Annotated[str | Path | None, Option()] = None,
    range_param: RangeParam | None = None,
) -> None:
    from pytoy.shared.lib.text import LineRange
    from pytoy.tools.console import ConsoleRunner

    if range_param is None:
        raise ValueError("`range_param` is None")
    line_range = LineRange(start=range_param.start, end=range_param.end)
    ConsoleRunner().send(buffer, driver, line_range, cwd=cwd)


@app.command("ConsoleStop")
def console_stop(buffer: Annotated[str, Option()] = "__TERMINAL__") -> None:
    from pytoy.tools.console import ConsoleRunner

    ConsoleRunner().stop(buffer)


@app.command("ConsoleTerminate")
def console_terminate(buffer: Annotated[str, Option()] = "__TERMINAL__") -> None:
    from pytoy.tools.console import ConsoleRunner

    ConsoleRunner().terminate(buffer)


group = Group("Script")


@group.command("run")
def script_run(path: Annotated[Path | None, Option()] = None, cwd: Annotated[Path | None, Option()] = None):
    from pytoy.shared.ui import PytoyBuffer
    from pytoy.tools.python import PythonExecutor

    path = path or PytoyBuffer.get_current().file_path
    from pytoy.shared.ui import PytoyBuffer

    match path.suffix:
        case ".py" | ".pyi":
            executor = PythonExecutor()
            if executor.is_running:
                raise RuntimeError("Currently, `PythonExecutor` is running.")
            from pytoy.shared.ui import make_duo_buffers

            stdout_buffer, stderr_buffer = make_duo_buffers(TERM_STDOUT, TERM_STDERR)
            executor.runfile(path, stdout_buffer, stderr_buffer)
        case _:
            raise ValueError(f"`{path.suffix=}` cannot be recognized.")


@group.command("rerun")
def script_rerun():
    from pytoy.shared.ui import make_duo_buffers
    from pytoy.tools.python import PythonExecutor

    executor = PythonExecutor()
    stdout_buffer, stderr_buffer = make_duo_buffers(TERM_STDOUT, TERM_STDERR)
    executor.rerun(stdout_buffer, stderr_buffer)


@group.command("stop")
def script_stop():
    from pytoy.contexts.pytoy import GlobalPytoyContext

    for item in GlobalPytoyContext.get().command_execution_manager.get_running():
        item.runner.terminate()


app = App()


@app.command("Hide")
def hide_buffers(scope: Annotated[Literal["temporary", "terminal"], Argument()]) -> None:
    from pytoy.shared.ui.pytoy_buffer import PytoyBufferProvider

    provider = PytoyBufferProvider()
    buffers = [buffer for buffer in provider.get_buffers(is_normal_type=False) if _matches_hide_scope(buffer, scope)]
    if not buffers:
        return

    _terminate_matching_executions(buffers)
    provider.close_buffers([buffer.buffer_id for buffer in buffers])


def _matches_hide_scope(buffer: PytoyBuffer, scope: Literal["temporary", "terminal"]) -> bool:
    if buffer.is_file or not buffer.source.name:
        return False
    name = Path(buffer.source.name).name
    if not name.startswith("__"):
        return False
    return scope == "temporary" or name in _TERMINAL_BUFFER_NAMES


def _terminate_matching_executions(buffers: Sequence[PytoyBuffer]) -> None:
    from pytoy.tool_execution.command import CommandExecutionHandler
    from pytoy.tool_execution.terminal import TerminalExecutionHandler, TerminalExecutionQuery
    from pytoy.tool_session.llm import LLMSessionHandler, LLMSessionQuery

    sources = {buffer.source for buffer in buffers}
    for source in sources:
        for handler in TerminalExecutionHandler.query(TerminalExecutionQuery(buffer=source)):
            _terminate_if_running(handler)
        for session in LLMSessionHandler.query(LLMSessionQuery(buffer_source=source)):
            session.terminate()

    for handler in CommandExecutionHandler.query():
        try:
            if handler.status != "running":
                continue
            stderr = handler.stderr
            matches = handler.stdout.source in sources or (stderr is not None and stderr.source in sources)
        except (RuntimeError, ValueError):
            continue
        if matches:
            _terminate_if_running(handler)


def _terminate_if_running(handler) -> None:
    try:
        status = handler.status
    except (RuntimeError, ValueError):
        return
    if status == "running":
        try:
            handler.terminate()
        except (RuntimeError, ValueError):
            pass
