from pytoy.job_execution.utils import get_current_directory

from pytoy.job_execution.terminal_executor import TerminalExecutor, TerminalExecution, BufferRequest, ExecutionRequest
from pytoy.job_execution.terminal_runner.drivers import TerminalDriverManager, TerminalDriverProtocol, DEFAULT_SHELL_DRIVER_NAME
from pytoy.contexts.pytoy import GlobalPytoyContext


from pathlib import Path 

from pytoy.shared.command import Argument, App, Option, RangeParam
from pytoy.shared.lib.text import LineRange
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from typing import Literal, Annotated


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
            buffer_req = BufferRequest(stdout=buffer_name)
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
        path = buffer.path
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



#@Command.register(name="Console", range=True)
#class TerminalController:
#
#    def __init__(self):
#        sub_commands = [
#            SubCommandSpec("run"),
#            SubCommandSpec("stop"),
#            SubCommandSpec("terminate"),
#        ]
#        ctx = GlobalPytoyContext.get()
#        self._driver_manager = ctx.terminal_driver_manager
#        driver_names = self._driver_manager.driver_names
#        self._execuiton_manager = ctx.terminal_execution_manager
#
#        main_options = [
#            OptionSpec("app", expects_value=True, completion=driver_names),
#            OptionSpec(
#                "buffer", expects_value=True, completion=["__TERMINAL__"]
#            ),
#            OptionSpec("cwd", expects_value=True, type=str)
#        ]
#
#        command_spec = MainCommandSpec(sub_commands, options=main_options)
#        self.handler = SubCommandsHandler(command_spec)
#
#    def __call__(self, opts: OptsArgument):
#        args: str = opts.args
#        parsed_arguments = self.handler.parse(args)
#        sub_command = parsed_arguments.sub_command
#        app_name: str | None = parsed_arguments.main_options.get("app")  #type: ignore
#        buffer: str | None = parsed_arguments.main_options.get("buffer") #type: ignore
#        cwd: Path | str | None = parsed_arguments.main_options.get("cwd") #type: ignore
#
#        if cwd is None:
#            cwd = get_current_directory()
#            
#        if sub_command == "run":
#            execution = self._get_or_create_execution(app_name, buffer, cwd=cwd)
#            content = " ".join(parsed_arguments.sub_arguments)
#            execution.runner.send(content)
#        elif sub_command == "stop":
#            execution = self._get_execution(app_name)
#            if execution:
#                execution.runner.interrupt()
#            else:
#                print("Target Executor is not existent.")
#        elif sub_command == "terminate":
#            executions = self._execuiton_manager.get_running()
#            for execution in executions:
#                execution.runner.terminate()
#            if not executions:
#                print("Target Executor is not existent.")
#        else:
#            assert opts.line1 is not None and opts.line2 is not None
#            execution = self._get_or_create_execution(app_name, buffer, cwd=cwd)
#            line_range = opts.line_range
#            assert line_range 
#            lines = PytoyBuffer.get_current().get_lines(line_range)
#            content = "\n".join(lines)
#            execution.runner.send(content)
#
#    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
#        """This is defined by `Command`."""
#        return self.handler.complete(arg_lead, cmd_line, cursor_pos)
#
#    def _get_execution(
#        self, driver_name: str | None) -> TerminalExecution | None:
#        # [TODO]:
#        #  Maybe, mupliple executions exist, due to the other systems (Very Edge Case)
#        driver_name = driver_name or self._select_preferrable_name()
#        executions = self._execuiton_manager.get_running(name=driver_name)
#        if executions:
#            return executions[0]
#        return None
#
#    def _get_or_create_execution(
#        self, driver_name: str | None, buffer_name: str | None = None, 
#        cwd: str | Path | None = None,
#    ) -> TerminalExecution:
#        # NOTE: In this Command, `name` and `driver_name` as the same one. 
#
#        driver_name = driver_name or self._select_preferrable_name()
#        executions = self._execuiton_manager.get_running(name=driver_name)
#        if not executions:
#            buffer_name = buffer_name or "__CMD__"
#            if buffer_name is None:
#                buffer_name = buffer_name
#            buffer_req = BufferRequest(stdout=buffer_name)
#            driver = self._driver_manager.create(driver_name=driver_name, name=driver_name)  # [TODO] Thsi is one of weakpoint unless to clarify the existence of `name` parameter.
#            execution_req = ExecutionRequest(driver=driver, command_wrapper="system", cwd=cwd)
#            executor = TerminalExecutor(buffer_req)
#            execution = executor.execute(execution_req)
#        else:
#            execution = executions[0]
#        return execution
#
#    # [TODO]: This logic is too specific, the target of refactor.
#    def _select_preferrable_name(self) -> str:
#        buffer = PytoyBuffer.get_current()
#        path = buffer.path
#        if path and path.suffix == ".py":
#            self._driver_manager._is_registered("ipython")
#            return "ipython"
#        return DEFAULT_SHELL_DRIVER_NAME
#