from pytoy.ui.vscode.document_user import sweep_editors
from pytoy.ui.windows_utils.protocol import WindowsUtilProtocol


class WindowsUtilVSCode(WindowsUtilProtocol):
    def sweep_windows(self) -> None:
        sweep_editors()

    def create_window(self, bufname: str):
        print("Currently, not yet implemented.")

