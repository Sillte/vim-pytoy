
from pytoy.tools.python import PythonExecutor


TERM_STDOUT = "__pystdout__"  # TERIMINAL NAME of `stdout`.
TERM_STDERR = "__pystderr__"  # TERIMINAL NAME of `stderr`.
IPYTHON_TERMINAL = None  # TERMINAL MANAGER for `ipython`.

# Python Execution Interface


def run(path=None):
    """Perform `python {path}`."""
    from pytoy.shared.ui import PytoyBuffer
    if not path:
        path = PytoyBuffer.get_current().file_path
    executor = PythonExecutor()
    if executor.is_running:
        raise RuntimeError("Currently, `PythonExecutor` is running.")

    from pytoy.shared.ui import make_duo_buffers

    stdout_buffer, stderr_buffer = make_duo_buffers(TERM_STDOUT, TERM_STDERR)

    executor.runfile(path, stdout_buffer, stderr_buffer)


def rerun():
    """Perform `python` with the previous `path`."""
    executor = PythonExecutor()

    from pytoy.shared.ui import make_duo_buffers, PytoyBuffer

    stdout_buffer, stderr_buffer = make_duo_buffers(TERM_STDOUT, TERM_STDERR)

    executor.rerun(stdout_buffer, stderr_buffer)


def stop():
    from pytoy.contexts.pytoy import GlobalPytoyContext
    for item in GlobalPytoyContext.get().command_execution_manager.get_running():
        item.runner.terminate()


def reset():
    """Reset the state of windows."""
    import vim
    vim.command(":lclose")
    for term in (TERM_STDOUT, TERM_STDERR):
        nr = int(vim.eval(f'bufwinnr("{term}")'))
        if 0 <= nr:
            vim.command(f":{nr}close")

# Command definitions.
# Maybe `Command` uses the public interfaces,
# Hence, `import`s are placed here.
from pytoy import commands  # NOQA

if __name__ == "__main__":
    print("__name__", __name__)
