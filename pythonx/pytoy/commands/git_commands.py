"""git_commands
"""
import vim 
from pathlib import Path
from pytoy.command import CommandManager
from pytoy.tools.git import get_remote_link

@CommandManager.register(name="GitAddress", range="")
def get_gitaddress(opts: dict):
    line1 = opts["line1"] 
    filepath = Path(vim.current.buffer.name)
    vim.current.buffer.name
    remote_link = get_remote_link(filepath, line1)
    vim.command(f'let @c="{remote_link}"')
    vim.command(f'let @*="{remote_link}"')
    print("@c/@*", remote_link)
    return remote_link

