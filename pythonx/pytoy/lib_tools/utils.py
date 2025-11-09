from pathlib import Path

import vim
from pytoy.ui.utils import to_filename
from pytoy.ui.pytoy_buffer import PytoyBuffer


def get_current_directory(buffer: PytoyBuffer | None = None) -> Path:
    """Return the current_directory.

    1. if the current buffer is regarded as file, then it is regarded
    2. if not, the `current directiony` of `(Nvim) is regarded as

    Rationale:
    When `vscode` and `neovim` are used the same time,
    it assumes different `current_folder` .
    This function is intended to resovle this.
    """
    if not buffer:
        buffer = PytoyBuffer.get_current()
    if buffer.is_file:
        filename = to_filename(buffer.path)
        current_folder = filename.parent
    else:
        cwd = vim.eval("getcwd()")
        current_folder = Path(cwd)

    return current_folder
