"""git_commands
"""
import vim 
from pathlib import Path
from pytoy.command import CommandManager
from pytoy.git_utils import git_user, get_remote_link

@CommandManager.register(name="GitAddress", range="")
def get_gitaddress(opts: dict):
    line1 = opts["line1"] 
    filepath = Path(vim.current.buffer.name)
    vim.current.buffer.name
    remote_link = get_remote_link(filepath, line1)
    vim.command(f'let @c="{remote_link}"')






