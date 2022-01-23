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
from pytoy.executor import BufferExecutor
from pytoy.sham_console import ShamConsole
from pytoy.venv_utils import VenvManager
from pytoy.lightline_utils import Lightline


TERM_STDOUT = "__pystdout__" # TERIMINAL NAME of `stdout`.
TERM_STDERR = "__pystderr__" # TERIMINAL NAME of `stderr`.
PYTOY_EXECUTOR = "PYTOY_EXECUTOR"

PREV_PATH = None  # Previously executed PATH. 

# Python Execution Interface

def run(path=None):
    """Perform `python {path}`. 
    """
    if not path:
        path = vim.current.buffer.name
    executor = PytoyExecutor(PYTOY_EXECUTOR)
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
    executor = PytoyExecutor(PYTOY_EXECUTOR)
    executor.stop()

def is_running() -> int:
    executor = PytoyExecutor(PYTOY_EXECUTOR)
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

def send_current_line():
    console = IPythonConsole(TERM_STDOUT)
    console.send_current_line()

def send_current_range():
    console = IPythonConsole(TERM_STDOUT)
    console.send_current_range()
    

class PytoyExecutor(BufferExecutor):
    def prepare(self, options) -> None:
        vimfunc_name = PytoyVimFunctions.register(self.on_closed, prefix=f"{self.jobname}_VIMFUNC")
        options["exit_cb"] = vimfunc_name

    def on_closed(self): 
        # vim.Function("setloclist") seems to more appropriate, 
        # but it does not work correctly with Python 3.9. 
        setloclist = vim.bindeval('function("setloclist")')

        error_msg = "\n".join(self.stderr)
        if error_msg:
            qflist = self._make_qflist(error_msg)
            setloclist(self.win_id, qflist)  
        else:
            setloclist(self.win_id, [])  # Reset `LocationList`.
            with store_window():
                vim.eval(f"win_gotoid({self.win_id})")
                vim.command(f"lclose")

            nr = int(vim.eval(f'bufwinnr({self.stderr.number})'))
            if 0 <= nr:
                vim.command(f':{nr}close')

            # Scrolling output window
            with store_window():
                stdout_id = vim.eval(f"bufwinid({self.stdout.number})")
                vim.command(f"call win_gotoid({stdout_id})")
                vim.command(f"normal zb")

        # Unregister of Job.
        vim.command(f"unlet g:{self.jobname}")

    def _make_qflist(self, string):
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


class IPythonConsole:
    __cache = dict()
    def __new__(cls, buf, display_interval=0.1):
        """ Singleton,  
        """
        stdout_window = create_window(buf, "vertical")
        buf = to_buffer_number(buf)
        if buf in cls.__cache:
            target = cls.__cache[buf]
            target.display_interval = display_interval
            return target
        self = object.__new__(cls)
        self._init_(buf, display_interval)
        cls.__cache[buf] = self
        return self

    def _init_(self, buf, display_interval:float=0.1): 
        # To prevent muptile calling of `__init__`, 
        # you have to the processing inside `__new__`.
        self.buffer_number = to_buffer_number(buf)
        self.sham_console = ShamConsole()
        self.sham_console.start()
        self._is_alive = True
        self.display_interval = display_interval
        # I found that the order is important.
        # If you perform `self._thread.start()` in prior to 
        # the settings of member variables, with high probabilities
        # it failed. 

        # Here `daemon=True` seems to be necessary for the case  
        # vim is stopped from users. 
        self._thread = Thread(target=self._update, daemon=True)
        self._thread.start()

    def __init__(self, *args, **kwargs):
        pass


    def send(self, text):
        """Send the text to `ShameConsole`
        """
        self.sham_console.send(text)

    def send_current_line(self):
        line = vim.current.line
        self.send(line + "\n")

    def send_current_range(self):
        lines = ""
        for line in vim.current.range:
            lines += line
        lines += "\n\n"   # It seems empty line is necessary.
        self.send(lines)


    def kill(self):
        self._is_alive = False
        self.sham_console.kill()

    def _update(self):
        while self._is_alive:
            time.sleep(self.display_interval)
            try:
                diff = self.sham_console.get_stdout()
            except Exception as e:
                diff = str(e)
            else:
                buf = vim.buffers[self.buffer_number]
                if not diff.strip():
                    continue
                for line in diff.split("\n"):
                    buf.append(line)


if __name__ == "__main__":
    print(__name__)

