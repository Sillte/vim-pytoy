from pytoy.ui import get_ui_enum, UIEnum
from pytoy.ui.windows_utils.protocol import WindowsUtilProtocol

windows_util_instance = None

def get_windows_util() -> WindowsUtilProtocol:
    if get_ui_enum() == UIEnum.VSCODE:
        from pytoy.ui.windows_utils.impl_vscode  import WindowsUtilVSCode
        return WindowsUtilVSCode()
    else:
        from pytoy.ui.windows_utils.impl_vim  import WindowsUtilVim
        return WindowsUtilVim()


def sweep_windows() -> None:
    """Delete all the windows
    [NOTE]: There exist some difference about specification.

    In `sweep_windows_vscode`, `closeOtherEditors` are called,
    while in `sweep_windows_vim` the left window remains.

    """
    windows_util = get_windows_util()
    return windows_util.sweep_windows()

def is_leftwindow() -> bool:
    windows_util = get_windows_util()
    return windows_util.is_leftwindow()

def create_window(bufname: str):
    windows_util = get_windows_util()
    windows_util.create_window(bufname) 


if __name__ == "__main__":
    get_ui_enum()
