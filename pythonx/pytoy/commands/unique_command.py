from pytoy.infra.command import Command
from pytoy.infra.command.models import OptsArgument
from pytoy.ui.pytoy_window import PytoyWindow

from pytoy.infra.sub_commands import (
    MainCommandSpec,
    SubCommandSpec,
    SubCommandsHandler,
)

BUFFER_ARG = "buffer"
EDITOR_ARG = "editor"
WINDOW_ARG = "window"
TAB_ARG = "tab"


@Command.register(name="Unique")
class UniqueCommand:
    def __init__(self):
        sub_commands = [
            SubCommandSpec(BUFFER_ARG),
            SubCommandSpec(EDITOR_ARG),
            SubCommandSpec(WINDOW_ARG),
            SubCommandSpec(TAB_ARG),
        ]
        command_spec = MainCommandSpec(sub_commands)
        self.handler = SubCommandsHandler(command_spec)

    def __call__(self, opts: OptsArgument):
        args: str = opts.args
        parsed_arguments = self.handler.parse(args)
        sub_command = parsed_arguments.sub_command

        if sub_command in {BUFFER_ARG}:
            within_tabs = True
            within_windows = True
        elif sub_command in {EDITOR_ARG, WINDOW_ARG}:
            within_tabs = False
            within_windows = True
        elif sub_command in {TAB_ARG}:
            within_tabs = True
            within_windows = False
        else:
            if 2 <= len(PytoyWindow.get_windows()):
                within_tabs = False
                within_windows = True
            else:
                within_tabs = True
                within_windows = False
        current = PytoyWindow.get_current()
        current.unique(within_tabs=within_tabs, within_windows=within_windows)

    def customlist(self, arg_lead: str, cmd_line: str, cursor_pos: int):
        return self.handler.complete(arg_lead, cmd_line, cursor_pos)