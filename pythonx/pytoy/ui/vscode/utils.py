import time
from pathlib import Path
from pytoy.ui.vscode.uri import Uri
from pytoy.ui.vscode.api import Api
from pytoy.infra.core.models import CursorPosition
from pytoy.ui.pytoy_window import PytoyWindow



def wait_until_true(
    condition_func, timeout: float = 3.0, n_trials: int = 10, initial_wait=None
) -> bool:
    """Wait the `condition_func` returns true.
    If `timeout` passes and this func returns False.
    """
    import vim

    interval = timeout / n_trials
    for _ in range(n_trials):
        if condition_func():
            return True
        # It is required to procced functions in other loops.
        vim.command(f'sleep 1m') # Mpve events.
        vim.command('redraw')  # ←  RPC チャネルを処理
        time.sleep(interval)

    return False


def open_file(path: str | Path, position: CursorPosition | None = None) -> None:
    from pytoy.ui.vscode.document import Document
    path = Path(path)

    uri = Uri.from_filepath(path)
    if position:
        vscode_position = (position.line, position.col)
    else:
        vscode_position = None
    Document.open(uri, vscode_position)
