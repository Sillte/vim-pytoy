"""git_commands"""
from pytoy.shared.command import App, RangeParam
from pytoy.tools.git import get_remote_link
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer

app = App()

@app.command(name="GitAddress")
def get_gitaddress(line_range: RangeParam):
    start = line_range.start
    end = line_range.end
    filepath = PytoyBuffer.get_current().file_path

    remote_link = get_remote_link(filepath, start + 1, end)  # 1-based, inclusive.
    # TODO: It is required to eliminate explicit usage of `vim`.
    try:
        import vim
    except ImportError:
        pass
    else:
        vim.command(f'let @c="{remote_link}"')
        vim.command(f'let @*="{remote_link}"')
    print("@c/@*", remote_link)
    return remote_link
