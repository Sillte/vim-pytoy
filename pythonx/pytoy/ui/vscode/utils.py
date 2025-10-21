import time 
from pathlib import Path

def wait_until_true(condition_func, timeout: float=3.0, n_trials: int=3, initial_wait=None) -> bool:
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
    from pytoy.ui.vscode.api import Api
    api = Api()
    code = """
(async () => {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) return false;
    const uri = folders[0].uri;
    return uri.scheme === 'vscode-remote';
})()
"""
    return api.eval_with_return(code)

def open_file(path: str | Path):
    path = Path(path)
    from pytoy.ui.vscode.api import Api
    if is_remote_vscode():
        code = """
    (async (path) => {
        function getRemoteScheme() {
            const folders = vscode.workspace.workspaceFolders;
            if (!folders || folders.length === 0) return undefined;
            const uri = folders[0].uri;
            if (uri.scheme === 'vscode-remote') {
                return `vscode-remote://${uri.authority}`;
            }
            return undefined;
        }
        const scheme = getRemoteScheme()
        let uri; 
        if (scheme){
            uri = vscode.Uri.parse(`${scheme}${path}`);
        }
        else {
            uri = vscode.Uri.file(path);
        }
        vscode.commands.executeCommand(
            'vscode.open',
            uri,
        )
    })(args.path)
"""
        Api().eval_with_return(code, args={"args": {"path": path.as_posix()}})
    else:
        import vim
        vim.command(f"Edit {path.as_posix()}")
