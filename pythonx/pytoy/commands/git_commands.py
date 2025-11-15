"""git_commands"""

import vim
from pathlib import Path
from pytoy.command import CommandManager, OptsArgument
from pytoy.tools.git import get_remote_link
from pytoy.ui import to_filepath
from pytoy.ui.pytoy_buffer import PytoyBuffer


@CommandManager.register(name="GitAddress", range="")
def get_gitaddress(opts: OptsArgument):
    line1 = opts.line1
    line2 = opts.line2

    filepath = to_filepath(PytoyBuffer.get_current().path)
    import subprocess

    remote_link = get_remote_link(filepath, line1, line2)
    vim.command(f'let @c="{remote_link}"')
    vim.command(f'let @*="{remote_link}"')
    print("@c/@*", remote_link)
    return remote_link
