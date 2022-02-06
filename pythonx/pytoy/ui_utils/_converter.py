"""Converter
"""

import vim
from contextlib import contextmanager
from typing import Dict


def to_buffer_number(arg) -> int:
    """Convert To Number of Buffer."""
    try:
        arg = int(arg)
    except (TypeError, ValueError):
        try:
            arg = int(arg.number)
        except (AttributeError, ValueError):
            if isinstance(arg, str):
                arg = int(vim.eval(f'bufnr("{arg}")'))
            else:
                raise ValueError("Invalid Arugment in `to_buffer_number`.", arg)
    return arg


def to_tabpage_number(arg) -> int:
    """Convert `arg` to the number of tabpage."""
    try:
        arg = int(arg)
    except (TypeError, ValueError):
        try:
            arg = int(arg.number)
        except (AttributeError, ValueError):
            if isinstance(arg, str):
                arg = int(vim.eval(f'tabpagenr("{arg}")'))
            else:
                raise ValueError("Invalid Arugment in `to_tabpage_number`.", arg)
    return arg


def to_window_number(arg, tabnr=None) -> int:
    """Convert `arg` to `window number`."""
    try:
        arg = int(arg)
    except (TypeError, ValueError):
        try:
            arg = int(arg.number)
        except (AttributeError, ValueError):
            if isinstance(arg, str):
                if tabnr is None:
                    arg = int(vim.eval(f'winnr("{arg}")'))
                else:
                    tabnr = to_tabpage_number(tanbr)
                    arg = int(vim.eval(f'tabpagewinnr("{tabnr}", "{arg}")'))
            else:
                raise ValueError("Invalid Arugment in `to_window_number`.", arg)
    else:
        if arg <= 1000:
            return arg
        else:
            arg = int(vim.eval(f'win_id2win("{arg}")'))
    return arg


def to_window_id(arg) -> int:
    """Convert `arg` to the window-id."""
    try:
        arg = int(arg)
    except (TypeError, ValueError):
        arg = to_window_number(arg)

    if 1000 <= arg:
        return arg
    else:
        return int(vim.eval(f"win_getid('{arg}')"))
    return arg


# Not yet thoroughly tested (2020/02/06)
def to_buffer(arg) -> "buffer":
    def _is_buffer(arg):
        if hasattr(arg, "vars"):
            return True
        return False

    if _is_buffer(arg):
        return arg
    if isinstance(arg, str):
        arg = int(vim.eval(f'bufnr("{arg}")'))
        if arg == -1:
            raise ValueError("Specified `buffer` string does not exist.")
    if isinstance(arg, int):
        return vim.buffers[arg]
    raise ValueError("Invalid Argument in `to_buffer`.", arg)
