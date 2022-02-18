import vim
import subprocess
import re
import time
from threading import Thread

from pytoy.ui_utils import to_buffer_number, init_buffer, create_window, store_window
from pytoy.debug_utils import reset_python

# This `import` is required for `PytoyVimFunctions.register.vim.command.__name__` for Linux environment.
from pytoy import func_utils

from pytoy.func_utils import PytoyVimFunctions, with_return
from pytoy.venv_utils import VenvManager
from pytoy.lightline_utils import Lightline
from pytoy.ipython_terminal import IPythonTerminal

from pytoy.python_executor import PythonExecutor
from pytoy.pytest_executor import PytestExecutor
from pytoy.quickfix_handler import QuickFixFilter, QuickFixSorter

TERM_STDOUT = "__pystdout__"  # TERIMINAL NAME of `stdout`.
TERM_STDERR = "__pystderr__"  # TERIMINAL NAME of `stderr`.
IPYTHON_TERMINAL = None  # TERMINAL MANAGER for `ipython`.

# Python Execution Interface


def run(path=None):
    """Perform `python {path}`."""
    if not path:
        path = vim.current.buffer.name
    executor = PythonExecutor()
    if executor.is_running:
        raise RuntimeError(f"Currently, `PythonExecutor` is running.")

    stdout_window = create_window(TERM_STDOUT, "vertical")
    stderr_window = create_window(TERM_STDERR, "horizontal", stdout_window)
    executor.run(path, stdout_window.buffer, stderr_window.buffer)


def rerun():
    """Perform `python` with the previous `path`."""
    executor = PythonExecutor()
    stdout_window = create_window(TERM_STDOUT, "vertical")
    stderr_window = create_window(TERM_STDERR, "horizontal", stdout_window)
    executor.rerun(stdout_window.buffer, stderr_window.buffer)


def stop():
    executor = PythonExecutor()
    executor.stop()


def is_running() -> int:
    executor = PythonExecutor()
    ret = executor.is_running
    vim.command(f"let g:pytoy_return = {int(ret)}")
    return ret


def reset():
    """Reset the state of windows."""
    vim.command(":lclose")
    for term in (TERM_STDOUT, TERM_STDERR):
        nr = int(vim.eval(f'bufwinnr("{term}")'))
        if 0 <= nr:
            vim.command(f":{nr}close")


## Virtual Environment Interface


def activate():
    args = vim.eval("a:000")
    if args:
        name = args[0]
    else:
        name = None
    venv_manager = VenvManager()
    venv_manager.activate(name)
    Lightline().register(venv_manager.name)


def deactivate():
    venv_manager = VenvManager()
    Lightline().deregister(venv_manager.name)
    venv_manager.deactivate()


@with_return
def envinfo():
    venv_manager = VenvManager()
    info = str(venv_manager.envinfo)
    print(info)
    return venv_manager.envinfo


def term():
    """Open the terminal window
    with virtual environment.
    """
    venv_manager = VenvManager()
    venv_manager.term_start()


## Jedi Releated Interface.


def goto():
    """Go to the definition of the current word."""
    from pytoy import jedi_utils

    jedi_utils.goto()


## IPython Interface.

def _get_ipython_terminal():
    global IPYTHON_TERMINAL
    if IPYTHON_TERMINAL is None:
        IPYTHON_TERMINAL = IPythonTerminal(TERM_STDOUT)
    IPYTHON_TERMINAL.assure_alive()
    return IPYTHON_TERMINAL


def ipython_send_line():
    term = _get_ipython_terminal()
    term.send_current_line()


def ipython_send_range():
    term = _get_ipython_terminal()
    term.send_current_range()

def ipython_stop():
    term = _get_ipython_terminal()
    term.stop()


def ipython_reset():
    term = _get_ipython_terminal()
    term.reset_term()


def ipython_history():
    # Transcript all the buffer to `output_buffer`.
    term = _get_ipython_terminal()
    term.transcript()


## Pytest Interface.


def pytest_runall():
    executor = PytestExecutor()
    stdout_window = create_window(TERM_STDOUT, "vertical")
    executor.runall(stdout_window.buffer)


def pytest_runfile():
    executor = PytestExecutor()
    path = vim.current.buffer.name
    stdout_window = create_window(TERM_STDOUT, "vertical")
    executor.runfile(path, stdout_window.buffer)


def pytest_runfunc():
    executor = PytestExecutor()
    path = vim.current.buffer.name
    line = vim.Function("line")(".")
    stdout_window = create_window(TERM_STDOUT, "vertical")
    executor.runfunc(path, line, stdout_window.buffer)

## QuickFix Interface.

def quickfix_gitfilter():
    fix_filter = QuickFixFilter()
    fix_filter.restrict_on_git()

def quickfix_timesort():
    fix_sorter = QuickFixSorter()
    fix_sorter.sort_by_time()


if __name__ == "__main__":
    print(__name__)
