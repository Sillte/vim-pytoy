python3 << EOF
# Makeshift tests for CommandManager.register / exist / deregister.
import vim 
from pytoy.lib_tools.terminal_backend.executor import TerminalExecutorManager, TerminalExecutor
from pytoy.tools import terminal_applications  # noqa
from pytoy.tools.terminal_applications import get_default_app_name 
from pytoy.infra.sub_commands import (
    MainCommandSpec,
    SubCommandSpec,
    OptionSpec,
    SubCommandsHandler,
)

sub_commands = [
    SubCommandSpec("run"),
]

main_options = [
    OptionSpec("app", expects_value=True, short_option="a"), 
    OptionSpec("flag", expects_value=False, short_option="f"),
]


command_spec = MainCommandSpec(sub_commands, options=main_options)
handler = SubCommandsHandler(command_spec)

cmd_line = "--flag run hogegeh"

print(handler.parse(cmd_line))


EOF

