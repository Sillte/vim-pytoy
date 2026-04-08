from pytoy.job_execution.utils import get_current_directory

from pytoy.job_execution.terminal_executor import TerminalExecutor, TerminalExecution, BufferRequest, ExecutionRequest
from pytoy.job_execution.terminal_runner.drivers import TerminalDriverManager, TerminalDriverProtocol, DEFAULT_SHELL_DRIVER_NAME
from pytoy.contexts.pytoy import GlobalPytoyContext

from pathlib import Path 

from pytoy.shared.command import Argument, App, Option, RangeParam, Group
from pytoy.shared.lib.text import LineRange
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from typing import Literal, Annotated
from pytoy import TERM_STDERR, TERM_STDOUT


class ConsoleController:

    @classmethod
    def get_execution(
        cls, driver_name: str | None) -> TerminalExecution | None:
        # [TODO]:
        #  Maybe, mupliple executions exist, due to the other systems (Very Edge Case)
        driver_name = driver_name or cls._select_preferrable_name()
        executions = cls.get_execution_manager().get_running(name=driver_name)
        if executions:
            return executions[0]
        return None


    @classmethod
    def get_or_create_execution(
        cls, driver_name: str | None, buffer_name: str | None = None, 
        cwd: str | Path | None = None,
    ) -> TerminalExecution:
        # NOTE: In this Command, `name` and `driver_name` as the same one. 

        driver_name = driver_name or cls._select_preferrable_name()
        executions = cls.get_execution_manager().get_running(name=driver_name)
        if not executions:
            buffer_name = buffer_name or "__CMD__"
            buffer_req = BufferRequest.from_no_file(buffer_name)
            driver = cls.get_driver_manager().create(driver_name=driver_name, name=driver_name)  # [TODO] Thsi is one of weakpoint unless to clarify the existence of `name` parameter.
            execution_req = ExecutionRequest(driver=driver, command_wrapper="system", cwd=cwd)
            executor = TerminalExecutor(buffer_req)
            execution = executor.execute(execution_req)
        else:
            execution = executions[0]
        return execution

    # [TODO]: This logic is too specific, the target of refactor.
    @classmethod
    def _select_preferrable_name(cls) -> str:
        buffer = PytoyBuffer.get_current()
        if buffer.is_file:
            path = buffer.file_path
        else:
            path = None
        if path and path.suffix == ".py":
            driver_manager = cls.get_driver_manager()
            if driver_manager._is_registered("ipython"):
                return "ipython"
        return DEFAULT_SHELL_DRIVER_NAME
    
    @classmethod
    def get_driver_manager(cls):
        ctx = GlobalPytoyContext.get()
        return ctx.terminal_driver_manager


    @classmethod
    def get_execution_manager(cls):
        ctx = GlobalPytoyContext.get()
        return ctx.terminal_execution_manager


app = App()

@app.command("Console")
def console(kind: Annotated[Literal["run", "stop", "terminate"] | None,  Argument()] = None,
            driver: Annotated[str | None, Option()] = None,
            buffer: Annotated[str, Option()] = "__TERMINAL__",
            cwd: Annotated[str | Path | None, Option()] = None, 
            cmd: Annotated[str | None, Argument()] = None,
            range_param: RangeParam | None = None, 
            ):

    cwd = Path(cwd) if cwd else Path(get_current_directory())
    cmd = cmd or ""

    match kind:
        case "run":
            execution = ConsoleController.get_or_create_execution(driver, buffer, cwd=cwd)
            execution.runner.send(cmd)
        case "stop":
            if (execution := ConsoleController.get_execution(driver)):
                execution.runner.interrupt()
            else:
                print("Target Executor is not existent.")
        case "terminate":
            executions = ConsoleController.get_execution_manager().get_running()
            for execution in executions:
                execution.runner.terminate()
            if not executions:
                print("Target Executor is not existent.")
        case None:
            execution = ConsoleController.get_or_create_execution(driver, buffer, cwd=cwd)
            if range_param is None:
                raise ValueError("`range_param` is None")
            line_range = LineRange(start=range_param.start, end= range_param.end)
            lines = PytoyBuffer.get_current().get_lines(line_range)
            content = "\n".join(lines)
            execution.runner.send(content)
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
    source1 = BufferSource(name=TERM_STDOUT, type="nofile")
    source2 = BufferSource(name=TERM_STDERR, type="nofile")
    provider = PytoyBufferProvider()
    buffers = provider.query(BufferQuery(buffer_sources=[source1, source2]))

    #print("buffers", buffers)
    for buffer in buffers:
        buffer.hide()


