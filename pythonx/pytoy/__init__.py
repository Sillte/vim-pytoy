import vim

from pytoy.lib_tools.environment_manager import EnvironmentManager
from pytoy.lib_tools.environment_manager.venv_utils import VenvManager
from pytoy.ui.lightline_utils import Lightline
from pytoy.tools.ipython_terminal import IPythonTerminal

from pytoy.tools.python_executor import PythonExecutor


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

    from pytoy.ui import make_duo_buffers, PytoyBuffer

    stdout_buffer, stderr_buffer = make_duo_buffers(TERM_STDOUT, TERM_STDERR)

    executor.runfile(path, stdout_buffer, stderr_buffer)


def rerun():
    """Perform `python` with the previous `path`."""
    executor = PythonExecutor()

    from pytoy.ui import make_duo_buffers, PytoyBuffer

    stdout_buffer, stderr_buffer = make_duo_buffers(TERM_STDOUT, TERM_STDERR)

    executor.rerun(stdout_buffer, stderr_buffer)


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


# Command definitions.
# Maybe `Command` uses the public interfaces,
# Hence, `import`s are placed here.
from pytoy import commands  # NOQA

if __name__ == "__main__":
    print("__name__", __name__)
