from pytoy.infra.command import Command, OptsArgument
from pytoy.ui.pytoy_window import PytoyWindow

from pytoy.infra.sub_commands import (
    MainCommandSpec,
    SubCommandSpec,
    SubCommandsHandler,
)

BUFFER_ARG = "buffer"
EDITOR_ARG = "editor"
WINDOW_ARG = "window"


@Command.register(name="Unique")
class UniqueCommand:
    def __init__(self):
        sub_commands = [
            SubCommandSpec(BUFFER_ARG),
            SubCommandSpec(EDITOR_ARG),
            SubCommandSpec(WINDOW_ARG),
        ]
        command_spec = MainCommandSpec(sub_commands)
        self.handler = SubCommandsHandler(command_spec)

    def __call__(self, opts: OptsArgument):
        args: str = opts.args
        parsed_arguments = self.handler.parse(args)
        arg = (
            parsed_arguments.main_arguments[0]
            if parsed_arguments.main_arguments
            else None
        )
        within_tab = False
        if arg in {BUFFER_ARG}:
            within_tab = False
        else:
            within_tab = True
        current = PytoyWindow.get_current()
        current.unique(within_tab=within_tab)

    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
        return self.handler.complete(arg_lead, cmd_line, cursor_pos)
