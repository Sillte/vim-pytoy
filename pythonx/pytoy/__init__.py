import vim
import subprocess
import re
import time
from threading import Thread

from pytoy.ui_utils import to_buffer_number, init_buffer, create_window, store_window
from pytoy.debug_utils import reset_python

# This is required for `PytoyVimFunctions.register.vim.command.__name__` for Linux environment.
from pytoy import func_utils 

from pytoy.func_utils import PytoyVimFunctions, with_return
from pytoy.venv_utils import VenvManager
from pytoy.lightline_utils import Lightline
from pytoy.ipython_terminal import IPythonTerminal

from pytoy.python_executor import PythonExecutor

TERM_STDOUT = "__pystdout__" # TERIMINAL NAME of `stdout`.
TERM_STDERR = "__pystderr__" # TERIMINAL NAME of `stderr`.
PYTOY_EXECUTOR = "PYTOY_EXECUTOR"
IPYTHON_TERMINAL = None  # TERMINAL MANAGER for `ipython`.

PREV_PATH = None  # Previously executed PATH. 

# Python Execution Interface

def run(path=None):
    """Perform `python {path}`. 
    """
    if not path:
        path = vim.current.buffer.name
    executor = PythonExecutor(PYTOY_EXECUTOR)
    if executor.is_running:
        raise RuntimeError(f"Currently, {PYTOY_EXECUTOR} is running.")

    command = f'python -u -X utf8 "{path}"'
    stdout_window = create_window(TERM_STDOUT, "vertical")
    stderr_window = create_window(TERM_STDERR, "horizontal", stdout_window)
    init_buffer(stdout_window.buffer)
    init_buffer(stderr_window.buffer)
    stdout_window.buffer[0] = f"`python {path}`"
    global PREV_PATH
    PREV_PATH = path
    executor.run(command, stdout_window.buffer, stderr_window.buffer)

def rerun():
    """Perform `python` with the previous `path`.
    """
    run(PREV_PATH)

def stop():
    executor = PythonExecutor(PYTOY_EXECUTOR)
    executor.stop()

def is_running() -> int:
    executor = PythonExecutor(PYTOY_EXECUTOR)
    ret =  executor.is_running
    vim.command(f"let g:pytoy_return = {int(ret)}")
    return ret

def reset():
    """Reset the state of windows. 
    """
    vim.command(':lclose')
    for term in (TERM_STDOUT, TERM_STDERR):
        nr = int(vim.eval(f'bufwinnr("{term}")'))
        if 0 <= nr:
            vim.command(f':{nr}close')

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
    """Go to the definition of the current word.
    """
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

def ipython_reset():
    term = _get_ipython_terminal()
    term.reset_term()

def ipython_history():
    # Transcript all the buffer to `output_buffer`.
    term = _get_ipython_terminal()
    term.transcript()
    

if __name__ == "__main__":
    print(__name__)

