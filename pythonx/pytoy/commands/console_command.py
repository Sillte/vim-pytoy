from pytoy.lib_tools.terminal_backend.executor import TerminalExecutorManager, TerminalExecutor
from pytoy.tools import terminal_applications  # noqa
from pytoy.tools.terminal_applications import get_default_app_name 
from pytoy.infra.command import Command, OptsArgument
from pytoy.ui.pytoy_buffer import PytoyBuffer

from pytoy.infra.sub_commands import (
    MainCommandSpec,
    SubCommandSpec,
    ArgumentSpec,
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

        app_candidates =  self.terminal_manager.app_manager.app_names

        main_options = [
            OptionSpec("app", expects_value=True, completion=app_candidates),
            OptionSpec(
                "buffer", expects_value=True, completion=["__CMD__", "__MOCK__"]
            ),
        ]

        command_spec = MainCommandSpec(sub_commands, options=main_options)
        self.handler = SubCommandsHandler(command_spec)

    def __call__(self, opts: OptsArgument):

        args: str = opts.args
        parsed_arguments = self.handler.parse(args)
        sub_command = parsed_arguments.sub_command
        app_name = parsed_arguments.main_options.get("app")
        buffer = parsed_arguments.main_options.get("buffer")

        if app_name or buffer:
            if app_name is None:
                # Todo, select the default app.
                app_name = get_default_app_name()
            if buffer is None:
                buffer =  "__CMD__"
            self._connect(str(app_name), str(buffer))

        if sub_command == "run":
            content = " ".join(parsed_arguments.sub_arguments)
            self.run(content)
        elif sub_command == "stop":
            self.stop()
        elif sub_command == "terminate":
            self.terminate()
        else:
            assert opts.line1 is not None and opts.line2 is not None
            line1, line2 =  opts.line1, opts.line2
            lines = PytoyBuffer.get_current().get_lines(line1, line2)
            content = "\n".join(lines)
            self.run(content)

    def run(self, content: str):
        executor = self.terminal_manager.current_executor
        if executor is None:
            # TODO: Choose the apt app default
            executor = self._connect()
        if not executor.alive:
            executor.start()
        executor.send(content)

    def stop(self):
        executor = self.terminal_manager.current_executor
        if executor is None:
            print("Currently, no terminal executors are running.")
            return
        executor.interrupt()

    def terminate(self):
        executor = self.terminal_manager.current_executor
        if executor is None:
            print("Currently, no terminal executors are running.")
            return
        executor.terminate()

    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
        """This is defined by `Command`.
        """
        return self.handler.complete(arg_lead, cmd_line, cursor_pos)

    def _connect(
        self, app_name: str | None = None, buffer_name: str | None = None
    ) -> TerminalExecutor:
        if not app_name:
            app_name = get_default_app_name()
        executor = self.terminal_manager.get_executor(
            app_name, buffer_name=buffer_name
        )
        if not executor.alive:
            executor.start()
        return executor
