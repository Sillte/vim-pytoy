"""
Utility function to handle `jedi-vim`.
* https://github.com/davidhalter/jedi-vim
"""
from pytoy import ui_utils
import vim 

def goto():
    ui_utils.sweep_windows(exclude=[vim.current.window])
    v = vim.eval("g:jedi#use_splits_not_buffers")
    if ui_utils.is_leftwindow():
        vim.command(f"let g:jedi#use_splits_not_buffers='right'")
    else:
        vim.command(f"let g:jedi#use_splits_not_buffers=''")

    vim.command(f"call g:jedi#goto()")
    vim.command(f"let g:jedi#use_splits_not_buffers='{v}'")

