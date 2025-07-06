from pytoy.ui.windows_utils.protocol import WindowsUtilProtocol
import vim


class WindowsUtilVim(WindowsUtilProtocol):
    def sweep_windows(self) -> None:
        from pytoy.ui.vim import sweep_windows as sweep_windows_vim
        window = vim.current.window
        sweep_windows_vim(required_width=1000, exclude=(window, ))

    def is_leftwindow(self) -> bool:
        from pytoy.ui.vim import is_leftwindow as is_leftwindow_vim
        return is_leftwindow_vim()

    def create_window(self, bufname: str):
        from pytoy.ui.vim import create_window as create_window_vim
        create_window_vim(bufname)
        

