import vim
import subprocess
import re
from pytoy.ui_utils import to_buffer_number, init_buffer, create_window
from pytoy.debug_utils import reset_python
from pytoy.func_utils import PytoyVimFunctions, with_return
from pytoy.executor import BufferExecutor
from pytoy.venv_utils import VenvManager


TERM_STDOUT = "__pystdout__" # TERIMINAL NAME of `stdout`.
TERM_STDERR = "__pystderr__" # TERIMINAL NAME of `stderr`.
PYTOY_EXECUTOR = "PYTOY_EXECUTOR"


def run():
    executor = PytoyExecutor(PYTOY_EXECUTOR)
    if executor.is_running:
        raise RuntimeError(f"Currently, {PYTOY_EXECUTOR} is running.")

    path = vim.current.buffer.name
    command = f'python -u -X utf8 "{path}"'
    stdout_window = create_window(TERM_STDOUT, "vertical")
    stderr_window = create_window(TERM_STDERR, "horizontal", stdout_window)
    init_buffer(stdout_window.buffer)
    init_buffer(stderr_window.buffer)
    executor.run(command, stdout_window.buffer, stderr_window.buffer)

def stop():
    executor = PytoyExecutor(PYTOY_EXECUTOR)
    executor.stop()

def is_running() -> int:
    executor = PytoyExecutor(PYTOY_EXECUTOR)
    ret =  executor.is_running
    vim.command(f"let l:ret = {int(ret)}")
    return ret

def activate():
    args = vim.eval("a:000")
    if args:
        name = args[0] 
    else:
        name = None
    venv_manager = VenvManager()
    venv_manager.activate(name)

def deactivate():
    venv_manager = VenvManager()
    venv_manager.deactivate()


@with_return
def envinfo():
    venv_manager = VenvManager()
    info = str(venv_manager.envinfo)
    print(info)
    return venv_manager.envinfo


def reset():
    """Reset the state of windows. 
    """
    vim.command(':lclose')
    for term in (TERM_STDOUT, TERM_STDERR):
        nr = int(vim.eval(f'bufwinnr("{term}")'))
        if 0 <= nr:
            vim.command(f':{nr}close')
    

class PytoyExecutor(BufferExecutor):
    def prepare(self, options) -> None:
        vimfunc_name = PytoyVimFunctions.register(self.on_closed, prefix=f"{self.jobname}_VIMFUNC")
        options["exit_cb"] = vimfunc_name

    def on_closed(self): 
        setloclist = vim.Function("setloclist")
        error_msg = "\n".join(self.stderr)
        if error_msg:
            qflist = make_qflist(error_msg)
            setloclist(self.win_id, qflist)  
        else:
            setloclist(self.win_id, [])  # Reset `LocationList`.
            c_id = vim.eval("win_getid()")
            vim.eval(f"win_gotoid({self.win_id})")
            vim.command(f"lclose")
            vim.eval(f"win_gotoid({c_id})")
            nr = int(vim.eval(f'bufwinnr({self.stderr.number})'))
            if 0 <= nr:
                vim.command(f':{nr}close')

        # Unregister of Job.
        vim.command(f"unlet g:{self.jobname}")

def make_qflist(string):
    """From string, construct `list` of `dict` for QuickFix.
    """
    _pattern = re.compile(r'\s+File "(.+)", line (\d+)')
    result = list()
    lines = string.split("\n")
    index = 0
    while index < len(lines): 
        infos = _pattern.findall(lines[index])
        if infos:
            filename, lnum = infos[0]
            row = dict()
            row["filename"] = filename
            row["lnum"] = lnum
            index += 1
            text = lines[index].strip()
            row["text"] = text
            result.append(row)
        index += 1
    result = list(reversed(result))
    return result


if __name__ == "__main__":
    print(__name__)



