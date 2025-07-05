import vim


def sweep_windows() -> None:
    from pytoy.ui.vim import sweep_windows as sweep_windows_vim  
    window = vim.current.window
    sweep_windows_vim(required_width=1000, exclude=(window, ))


def is_leftwindow() -> bool:
    from pytoy.ui.vim import is_leftwindow as is_leftwindow_vim  
    return is_leftwindow_vim()


def create_window(bufname: str) -> vim.Window:
    from pytoy.ui.vim import create_window as create_window_vim
    return create_window_vim(bufname)
