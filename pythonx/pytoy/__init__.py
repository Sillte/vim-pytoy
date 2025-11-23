import vim

from pytoy.lib_tools.environment_manager import EnvironmentManager
from pytoy.lib_tools.environment_manager.venv_utils import VenvManager
from pytoy.ui import lightline_utils
from pytoy.ui import to_filepath

from pytoy.tools.python import PythonExecutor


TERM_STDOUT = "__pystdout__"  # TERIMINAL NAME of `stdout`.
TERM_STDERR = "__pystderr__"  # TERIMINAL NAME of `stderr`.
IPYTHON_TERMINAL = None  # TERMINAL MANAGER for `ipython`.

# Python Execution Interface


def run(path=None):
    """Perform `python {path}`."""
    if not path:
        path = vim.current.buffer.name
        path = to_filepath(path)
    executor = PythonExecutor()
    if executor.is_running:
        raise RuntimeError("Currently, `PythonExecutor` is running.")

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
    from pytoy.lib_tools.buffer_executor.buffer_job_manager import BufferJobManager
    BufferJobManager.stop_all()


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


def term():
    """Open the terminal window
    with virtual environment.
    """
    from pytoy.lib_tools.environment_manager import EnvironmentManager, term_start
    term_start()


# Command definitions.
# Maybe `Command` uses the public interfaces,
# Hence, `import`s are placed here.
from pytoy import commands  # NOQA

if __name__ == "__main__":
    print("__name__", __name__)
