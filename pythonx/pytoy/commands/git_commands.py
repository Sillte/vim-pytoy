"""git_commands"""
from pytoy.shared.command.models import OptsArgument
from pytoy.command import CommandManager
from pytoy.tools.git import get_remote_link
from pytoy.shared.ui.utils import to_filepath
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer


@CommandManager.register(name="GitAddress", range="")
def get_gitaddress(opts: OptsArgument):
    line1 = opts.line1
    line2 = opts.line2

    filepath = to_filepath(PytoyBuffer.get_current().path)

    import vim
    remote_link = get_remote_link(filepath, line1, line2)
    vim.command(f'let @c="{remote_link}"')
    vim.command(f'let @*="{remote_link}"')
    print("@c/@*", remote_link)
    return remote_link
