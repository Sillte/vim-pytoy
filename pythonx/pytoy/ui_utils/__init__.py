import vim
from typing import Dict
from contextlib import contextmanager

# Conversion to the number or id.
from pytoy.ui_utils._converter import (
    to_buffer_number,
    to_window_number,
    to_tabpage_number,
    to_window_id,
    to_buffer,
)


def init_buffer(arg):
    """Empty the buffer."""
    bufnum = to_buffer_number(arg)
    if 0 < bufnum:
        vim.buffers[bufnum][:] = None


@contextmanager
def store_window():
    """Current window is retrieved, at the end of context."""
    winid = int(vim.eval(f"win_getid({vim.current.window.number})"))
    try:
        yield
    except Exception as e:
        vim.command(f":call win_gotoid({winid})")
        raise e
    else:
        vim.command(f":call win_gotoid({winid})")


def create_window(bufname, mode="vertical", base_window=None):
    """Append the specified `buffer` to `base_window` vertically or
    horizontally.

    """
    if base_window is None:
        base_window = vim.current.window

    storedwin = int(vim.eval(f"win_getid({vim.current.window.number})"))
    curwin = int(vim.eval(f"win_getid({base_window.number})"))

    if 0 < curwin:
        vim.command(f":call win_gotoid({curwin})")

    if mode.startswith("v"):
        split_type = "vertical belowright"
    else:
        split_type = "belowright"

    bufno = int(vim.eval(f'bufnr("{bufname}")'))
    if bufno <= 0:
        # Make a new Window.
        vim.command(f"{split_type} new {bufname}")
        window = vim.current.window
        window.buffer.options["buftype"] = "nofile"
        window.buffer.options["swapfile"] = False
    else:
        opt_switchbuf = vim.options["switchbuf"]
        vim.options["switchbuf"] = "useopen"
        vim.command(f"{split_type} sbuffer {bufname}")
        vim.options["switchbuf"] = opt_switchbuf
        window = vim.current.window

    if 0 < storedwin:
        vim.command(f":call win_gotoid({storedwin})")
    return window


def get_wininfos(tabnr=None) -> Dict:
    """Return informations of window
    Args:
        tabnr (tabpage).
    """
    if tabnr is None:
        tabnr = vim.current.tabpage
    tabnr = to_tabpage_number(tabnr)
    infos = vim.eval(f"getwininfo()")
    infos = [elem for elem in infos if elem["tabnr"] == str(tabnr)]
    return infos


def is_leftwindow(window=None):
    """Return whether `winnr` is `left` window or not."""
    if window is None:
        window = vim.current.window
    winid = to_window_id(window)
    info = vim.eval(f'getwininfo("{winid}")')
    if not info:
        raise ValueError(f"Invalid Argument, `{window}`.")
    else:
        info = info[0]

    return int(info["wincol"]) <= 1


def sweep_windows(required_width=100, exclude=()):
    """Sweep the windows of tabpage following to my rule.
    Namely,
    1. if the `winrow` is smaller than `required_width`.
    2. the window is not existent of the `left-most` position.
    """

    def _is_target(info):
        winnr = info["winnr"]
        if not is_leftwindow(winnr):
            if int(info["width"]) < required_width:
                return True
        return False

    infos = get_wininfos()
    infos = [info for info in infos if _is_target(info)]
    winnrs = [int(info["winnr"]) for info in infos]
    exclude = set(to_window_number(elem) for elem in exclude)
    for winnr in sorted(winnrs, reverse=True):
        if winnr not in exclude:
            vim.command(f"{winnr}close")


def create_buffer(bufname: str, options=None) -> "buffer":
    # It seems the generation of `buffer` may fail
    # due to interruption.
    # hence, retry mechanism is prepared.
    if options is None:
        options = dict()
    _retries = 3
    _wait_time = 0.1

    def _inner():
        bufno = int(vim.eval(f'bufnr("{bufname}")'))
        if not 0 < bufno:
            vim.command(f"vnew {bufname}")
            bufno = int(vim.eval(f'bufnr("{bufname}")'))
        return vim.buffers[bufno]

    for _ in range(_retries):
        try:
            buf = _inner()
        except:
            time.sleep(_wait_time)
        else:
            for key, value in options.items():
                buf[key] = value
            return buf
    return None
