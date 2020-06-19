import vim
from contextlib import contextmanager

def to_buffer_number(arg):
    """Convert To Number of Buffer.
    """
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


def init_buffer(arg):
    """ Empty the buffer.
    """
    bufnum = to_buffer_number(arg)
    if 0 < bufnum:
        vim.buffers[bufnum][:] = None

@contextmanager
def store_window():
    """Current window is retrieved, at the end of context. 
    """
    winid = int(vim.eval(f'win_getid({vim.current.window.number})'))
    try:
        yield
    except Exception as e:
        vim.command(f':call win_gotoid({winid})')
        raise e
    else:
        vim.command(f':call win_gotoid({winid})')

def create_window(bufname, mode="vertical", base_window=None):
    """Append the specified `buffer` to `base_window` vertically or
    horizontally.

    """
    if base_window is None:
        base_window = vim.current.window

    storedwin = int(vim.eval(f'win_getid({vim.current.window.number})'))
    curwin = int(vim.eval(f'win_getid({base_window.number})'))

    if 0 < curwin:
        vim.command(f':call win_gotoid({curwin})')

    if mode.startswith("v"):
        split_type = "vertical belowright"
    else:
        split_type = "belowright"

    bufno = int(vim.eval(f'bufnr("{bufname}")'))
    if bufno <= 0:
        # Make a new Window.
        vim.command(f'{split_type} new {bufname}')
        window = vim.current.window
        window.buffer.options["buftype"] = "nofile"
        window.buffer.options["swapfile"] = False
    else:
        opt_switchbuf = vim.options["switchbuf"]
        vim.options["switchbuf"] = "useopen"
        vim.command(f'{split_type} sbuffer {bufname}')
        vim.options["switchbuf"] = opt_switchbuf
        window = vim.current.window

    if 0 < storedwin:
        vim.command(f':call win_gotoid({storedwin})')
    return window

if __name__ == "__main__":
    pass

