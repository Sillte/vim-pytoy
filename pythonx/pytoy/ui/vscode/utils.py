import time
from pathlib import Path
from pytoy.ui.vscode.uri import Uri
from pytoy.ui.vscode.api import Api


def wait_until_true(
    condition_func, timeout: float = 3.0, n_trials: int = 3, initial_wait=None
) -> bool:
    """Wait the `condition_func` returns true.
    If `timeout` passes and this func returns False.
    """

    interval = timeout / n_trials
    if initial_wait is None:
        initial_wait = interval // 10
    time.sleep(initial_wait)
    for _ in range(n_trials):
        if condition_func():
            return True
        time.sleep(interval)
    return False

def is_remote_vscode() -> bool:
    return bool(Api().eval_with_return("vscode.env.remoteName"))

def get_remote_authority() -> str:
    if not is_remote_vscode():
        return ""
    
    uris = Uri.get_uris()
    uris = [uri for uri in uris if uri.scheme == "vscode-remote"]
    authorities = set(uri.authority for uri in uris)
    if 2 <= len(authorities):
        msg = f"`{authorities}` are found, it is impossible to determine autority."
        raise ValueError(msg)
    elif 1 == len(authorities): 
        return list(authorities)[0]

    # Inference based on working folder.
    api = Api()
    jscode = "vscode.workspace.workspaceFolders.map(folder => {folder.uri});"
    uris = [Uri.model_validate(elem) for elem in api.eval_with_return(jscode, with_await=False)]
    uris = [uri for uri in uris if uri.scheme == "vscode-remote"]
    authorities = set(uri.authority for uri in uris)
    if 2 <= len(authorities):
        msg = f"`{authorities}` are found, it is impossible to determine autority."
        raise ValueError(msg)
    elif 1 == len(authorities): 
        return list(authorities)[0]
    return ""

def open_file(path: str | Path, position: tuple[int, int] | None = None) -> None:
    path = Path(path)
    from pytoy.ui.vscode.api import Api
    from pytoy.ui.vscode.document import Document

    if is_remote_vscode():
        uri = Uri.from_filepath(path)
        Document.open(uri, position)
    else:
        import vim

        vim.command(f"Edit {path.as_posix()}")
        if position:
            lnum, col = position
            vim.command(f"call cursor({lnum}, {col})")