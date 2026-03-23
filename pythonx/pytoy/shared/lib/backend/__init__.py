from enum import StrEnum


class BackendEnum(StrEnum):
    VIM = "vim"
    NVIM = "nvim"
    VSCODE = "vscode" # This is neovim-vscode.
    DUMMY = "dummy"


__backend_enum: BackendEnum | None = None


def get_backend_enum() -> BackendEnum:
    global __backend_enum
    if __backend_enum is not None:
        return __backend_enum
    __backend_enum = _resolve_backend_enum()
    return __backend_enum

def can_use_vim() -> bool:
    # VSCODE means `neovim-vscode`, which is the plugin for vscode that provides neovim integration.
    return get_backend_enum() in (BackendEnum.VIM, BackendEnum.NVIM, BackendEnum.VSCODE)


def _resolve_backend_enum() -> BackendEnum:
    try:
        import vim
    except Exception:
        return BackendEnum.DUMMY

    try:
        result = int(vim.eval("1+1"))
        if result != 2:
            return BackendEnum.DUMMY
    except Exception:
        return BackendEnum.DUMMY

    if int(vim.eval("has('nvim')")):
        if int(vim.eval("exists('g:vscode')")):
            return BackendEnum.VSCODE
        return BackendEnum.NVIM
    return BackendEnum.VIM
