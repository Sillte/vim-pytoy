"""
"""
import vim 

from pytoy.ui import get_ui_enum, UIEnum
from pytoy.ui.vim import is_leftwindow as is_leftwindow_vim  
from pytoy.ui.vscode import focus_controller
from pytoy.ui.vscode.document import BufferURISolver

from pytoy.ui.vim import sweep_windows as sweep_windows_vim  
from pytoy.ui.vscode.document_user import sweep_editors as sweep_windows_vscode

from pytoy.ui.vim import sweep_windows as sweep_windows_vim  
from pytoy.ui.vim import create_window as create_window_vim


def sweep_windows() -> None:
    """Delete all the windows 
    [NOTE]: There exist some difference about specification.   

    In `sweep_windows_vscode`, `closeOtherEditors` are called, 
    while in `sweep_windows_vim` the left window remains.

    """
    ui_enum = get_ui_enum()
    if ui_enum == UIEnum.VSCODE:
        sweep_windows_vscode()
    else:
        window = vim.current.window
        sweep_windows_vim(required_width=1000, exclude=(window, ))


def is_leftwindow() -> bool:
    ui_enum = get_ui_enum()
    if ui_enum == UIEnum.VSCODE:
        bufnr = vim.current.buffer.number
        BufferURISolver.get_uri(bufnr)

        uri_to_views = focus_controller.get_uri_to_views()
        uri = BufferURISolver.get_uri(bufnr)
        if uri:
            viewnr = uri_to_views.get(uri)
        else:
            viewnr = None
        return viewnr == 1
    else:
        return is_leftwindow_vim(window=None)

def create_window(bufname: str):
    ui_enum = get_ui_enum()
    if ui_enum == UIEnum.VSCODE:
        pass

    else:
        return create_window_vim(bufname)


if __name__ == "__main__":
    pass
    get_ui_enum()
