from enum import Enum


class UIEnum(str, Enum):
    VIM = "VIM"
    NVIM = "NVIM"
    VSCODE = "VSCODE"  # vscode + neovim extension


def get_ui_enum() -> UIEnum:
    import vim

    if int(vim.eval("has('nvim')")):
        if int(vim.eval("exists('g:vscode')")):
            return UIEnum.VSCODE
        return UIEnum.NVIM
    return UIEnum.VIM
