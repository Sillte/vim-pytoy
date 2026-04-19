from pathlib import Path 

from pytoy.shared.command import Argument, App, Option, RangeParam, Group
from typing import Literal, Annotated
from pytoy import TERM_STDERR, TERM_STDOUT


app = App()

@app.command("Console")
def console(kind: Annotated[Literal["run", "stop", "terminate"] | None,  Argument()] = None,
            driver: Annotated[str | None, Option()] = None,
            buffer: Annotated[str, Option()] = "__TERMINAL__",
            cwd: Annotated[str | Path | None, Option()] = None, 
            cmd: Annotated[str | None, Argument()] = None,
            range_param: RangeParam | None = None, 
            ):
    from pytoy.shared.lib.text import LineRange
    from pytoy.tools.console import ConsoleRunner
    cmd = cmd or ""
    runner = ConsoleRunner()

    match kind:
        case "run":
            runner.run(cmd, buffer, driver, cwd=cwd)
        case "stop":
            runner.stop(buffer, driver, cwd=cwd)
        case "terminate":
            runner.terminate(buffer, driver)
        case None:
            if range_param is None:
                raise ValueError("`range_param` is None")
            line_range = LineRange(start=range_param.start, end=range_param.end)
            runner.send(buffer, driver, line_range, cwd=cwd)
        case _:
            raise ValueError(f"Unknown command. {kind}")


group = Group("Script") 
@group.command("run")
def script_run(path: Annotated[Path | None, Option()] = None, 
               cwd: Annotated[Path | None, Option()] = None):
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
    from pytoy.tools.python import PythonExecutor
    from pytoy.shared.ui import make_duo_buffers 
    executor = PythonExecutor()
    stdout_buffer, stderr_buffer = make_duo_buffers(TERM_STDOUT, TERM_STDERR)
    executor.rerun(stdout_buffer, stderr_buffer)
    
@group.command("stop")
def script_stop():
    from pytoy.contexts.pytoy import GlobalPytoyContext
    for item in GlobalPytoyContext.get().command_execution_manager.get_running():
        item.runner.terminate()

app = App()
@app.command("HideTemporary")
def hide_temporary():
    from pytoy.shared.ui import PytoyBufferProvider
    from pytoy.shared.ui.pytoy_buffer.models import BufferSource, BufferQuery
    source1 = BufferSource.from_no_file(name=TERM_STDOUT)
    source2 = BufferSource.from_no_file(name=TERM_STDERR)
    provider = PytoyBufferProvider()
    buffers = provider.query(BufferQuery(buffer_sources=[source1, source2]))

    #print("buffers", buffers)
    for buffer in buffers:
        buffer.hide()

