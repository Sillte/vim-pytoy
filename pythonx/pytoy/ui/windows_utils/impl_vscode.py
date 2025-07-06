import vim
from pytoy.ui.vscode.document_user import sweep_editors
from pytoy.ui.vscode import focus_controller
from pytoy.ui.vscode.document import BufferURISolver
from pytoy.ui.windows_utils.protocol import WindowsUtilProtocol


class WindowsUtilVSCode(WindowsUtilProtocol):
    def sweep_windows(self) -> None:
        sweep_editors()

    def is_leftwindow(self) -> bool:
        bufnr = vim.current.buffer.number
        uri = BufferURISolver.get_uri(bufnr)
        uri_to_views = focus_controller.get_uri_to_views()
        if uri:
            viewnr = uri_to_views.get(uri)
        else:
            viewnr = None
        return viewnr == 1

    def create_window(self, bufname: str):
        print("Currently, not yet implemented.")

