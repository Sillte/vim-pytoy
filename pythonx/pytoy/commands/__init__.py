"""In this submodule, `commands` 
"""
# Registration of commands
from pytoy.commands.pytools_commands import PyTestCommand, MypyCommand  # NOQA
from pytoy.commands.devtools_commands import VimReboot  # NOQA
from pytoy.commands.env_commands import UvToggle  # NOQA
from pytoy.commands.git_commands import get_gitaddress

from pytoy.commands.vscode_mock import *

