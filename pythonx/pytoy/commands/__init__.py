"""In this submodule, `commands`"""

# Registration of commands
from pytoy.commands import pytools_commands   # NOQA
#from pytoy.commands.devtools_commands import VimReboot  # NOQA
from pytoy.commands import devtools_commands  # NOQA
from pytoy.commands.git_commands import get_gitaddress  # NOQA
from pytoy.commands.env_commands import tool_chain_select  # NOQA

from pytoy.commands.experiment_commands import *
from pytoy.commands.vscode_commands import *
from pytoy.commands.vscode_mock import *

from pytoy.commands.console_command import TerminalController  # NOQA
from pytoy.commands.unique_command import unique_command  # NOQA
from pytoy.commands import llm_commands  # NOQA
