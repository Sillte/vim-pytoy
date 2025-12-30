import time
from pathlib import Path
from pytoy.ui.vscode.uri import Uri
from pytoy.ui.vscode.api import Api
from pytoy.infra.core.models import CursorPosition
from pytoy.ui.pytoy_window import PytoyWindow



def wait_until_true(
    condition_func, timeout: float = 3.0, n_trials: int = 3, initial_wait=None
) -> bool:
    """Wait the `condition_func` returns true.
    If `timeout` passes and this func returns False.
    """
    import vim


    interval = timeout / n_trials
    if initial_wait is None:
        initial_wait = interval / 10
        vim.command(f'sleep {round(initial_wait * 1000)}m')
    for _ in range(n_trials):
        if condition_func():
            return True
        # It is required to procced functions in other loops.
        vim.command(f'sleep {round(interval * 1000)}m')
        #time.sleep(interval)
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
