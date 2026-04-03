"""In this submodule, `commands`"""

# Registration of commands
from pytoy.commands import pytools_commands   # NOQA
from pytoy.commands import devtools_commands  # NOQA
from pytoy.commands.git_commands import get_gitaddress  # NOQA
from pytoy.commands.env_commands import tool_chain_select  # NOQA

from pytoy.commands import experiment_commands # NOQA
from pytoy.commands import vscode_commands # NOQA
from pytoy.commands import vscode_mock # NOQA

from pytoy.commands import console_command  # NOQA
from pytoy.commands.unique_command import unique_command  # NOQA
from pytoy.commands import llm_commands  # NOQA

