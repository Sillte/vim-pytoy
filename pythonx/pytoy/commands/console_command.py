from pytoy.lib_tools.terminal_backend.executor import (
    TerminalExecutorManager,
    TerminalExecutor,
)
from pathlib import Path 

from pytoy.lib_tools.utils import get_current_directory
from pytoy.tools import terminal_applications  # noqa
from pytoy.tools.terminal_applications import get_default_app_name
from pytoy.infra.command import Command
from pytoy.ui.pytoy_buffer import PytoyBuffer

from pytoy.infra.command import OptsArgument

from pytoy.infra.sub_commands import (
    MainCommandSpec,
    SubCommandSpec,
    OptionSpec,
    SubCommandsHandler,
)


@Command.register(name="Console", range=True)
class TerminalContoller:
    terminal_manager = TerminalExecutorManager

    def __init__(self):
        sub_commands = [
            SubCommandSpec("run"),
            SubCommandSpec("stop"),
            SubCommandSpec("terminate"),
        ]

        app_candidates = self.terminal_manager.app_manager.app_names

        main_options = [
            OptionSpec("app", expects_value=True, completion=app_candidates),
            OptionSpec(
                "buffer", expects_value=True, completion=["__CMD__", "__MOCK__"]
            ),
            OptionSpec("cwd", expects_value=True, type=str)
        ]

        command_spec = MainCommandSpec(sub_commands, options=main_options)
        self.handler = SubCommandsHandler(command_spec)

    def __call__(self, opts: OptsArgument):
        args: str = opts.args
        parsed_arguments = self.handler.parse(args)
        sub_command = parsed_arguments.sub_command
        app_name = parsed_arguments.main_options.get("app")
        buffer = parsed_arguments.main_options.get("buffer")
        cwd = parsed_arguments.main_options.get("cwd")

        if cwd is None:
            cwd = get_current_directory()
        
        def _decide_executor(app_name, buffer, none_ok: bool = True) -> TerminalExecutor | None:
            if app_name is None and buffer is None:
                executor = self.terminal_manager.current_executor
                if executor:
                    return executor
                if none_ok:
                    return None
            app_name = app_name or get_default_app_name()
            buffer = buffer or "__CMD__"
            executor = self.terminal_manager.get_executor(app_name, buffer)
            assert cwd is None or isinstance(cwd, (str, Path))
            return self._connect(app_name, buffer, cwd=cwd)

        if sub_command == "run":
            executor = _decide_executor(app_name, buffer, none_ok=False)
            assert executor is not None
            content = " ".join(parsed_arguments.sub_arguments)
            executor.send(content)
        elif sub_command == "stop":
            executor = _decide_executor(app_name, buffer, none_ok=True)
            if executor:
                executor.interrupt()
            else:
                print("Target Executor is not existent.")
        elif sub_command == "terminate":
            executor = _decide_executor(app_name, buffer, none_ok=True)
            if executor:
                executor.terminate()
            else:
                print("Target Executor is not existent.")
        else:
            assert opts.line1 is not None and opts.line2 is not None
            executor = _decide_executor(app_name, buffer, none_ok=False)
            assert executor is not None
            line1, line2 = opts.line1, opts.line2
            lines = PytoyBuffer.get_current().get_lines(line1, line2)
            content = "\n".join(lines)
            executor.send(content)

    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
        """This is defined by `Command`."""
        return self.handler.complete(arg_lead, cmd_line, cursor_pos)

    def _connect(
        self, app_name: str | None = None, buffer_name: str | None = None, 
        cwd: str | Path | None = None,
    ) -> TerminalExecutor:
        if not app_name:
            app_name = get_default_app_name()
        executor = self.terminal_manager.get_executor(app_name, buffer_name=buffer_name)
        if not executor.alive:
            executor.start(cwd=cwd)
        return executor
