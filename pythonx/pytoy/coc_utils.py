

from pytoy import ui_utils
import vim 

def goto():
    ui_utils.sweep_windows(exclude=[vim.current.window])


    if ui_utils.is_leftwindow():
        vim.command("rightbelow vsplit | wincmd l")
        vim.command("call CocAction('jumpDefinition')")
    else:
        vim.command("call CocAction('jumpDefinition')")

