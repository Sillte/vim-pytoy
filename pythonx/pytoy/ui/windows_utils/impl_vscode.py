import vim
from pytoy.ui.vscode.document_user import sweep_editors
from pytoy.ui.vscode import focus_controller
from pytoy.ui.vscode.document import BufferURISolver


def sweep_windows() -> None:
    sweep_editors()


def is_leftwindow() -> bool:
    bufnr = vim.current.buffer.number
    BufferURISolver.get_uri(bufnr)
    uri_to_views = focus_controller.get_uri_to_views()
    uri = BufferURISolver.get_uri(bufnr)
    if uri:
        viewnr = uri_to_views.get(uri)
    else:
        viewnr = None
    return viewnr == 1
