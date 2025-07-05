from pytoy.ui import get_ui_enum, UIEnum


def sweep_windows() -> None:
    """Delete all the windows
    [NOTE]: There exist some difference about specification.

    In `sweep_windows_vscode`, `closeOtherEditors` are called,
    while in `sweep_windows_vim` the left window remains.

    """
    ui_enum = get_ui_enum()
    if ui_enum == UIEnum.VSCODE:
        from pytoy.ui.windows_utils.impl_vscode import sweep_windows

        sweep_windows()
    else:
        from pytoy.ui.windows_utils.impl_vim import sweep_windows

        sweep_windows()


def is_leftwindow() -> bool:
    ui_enum = get_ui_enum()
    if ui_enum == UIEnum.VSCODE:
        from pytoy.ui.windows_utils.impl_vscode import is_leftwindow

        return is_leftwindow()
    else:
        from pytoy.ui.windows_utils.impl_vim import is_leftwindow

        return is_leftwindow()


def create_window(bufname: str):
    ui_enum = get_ui_enum()
    if ui_enum == UIEnum.VSCODE:
        print("Currently, not implemetend.")
    else:
        from pytoy.ui.windows_utils.impl_vim import create_window as create_window_vim

        return create_window_vim(bufname)


if __name__ == "__main__":
    get_ui_enum()
