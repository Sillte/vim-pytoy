import vim
import sys
from queue import Empty, Full, Queue

from pytoy.infra.timertask.timer import TimerTask
from typing import Any, Literal

# If you would like to Thread,
# `sys.stdout`, `sys.stderr` must be protected.
# so that these functions should be executed.
class _DummyPipe:
    """This class is used instead of `sys.stdout` /`sys.stderr`.
    """
    def __init__(self, queue: Queue):
        self._queue = queue

    def write(self, message: str) -> int:
        if message:
            try:
                self._queue.put_nowait(message)
            except Full:
                pass
        return len(message)

    def flush(self):
        pass


class StdoutProxy:
    """Fallback for `print` is called while using the `stdout` / `stderr`
    in the other thread in neovim / vim. 
    To address this need, we patch `sys.stdout` / `sys.stderr`. 
    """
    _timer_taskname: None | str  = None
    _stdout_queue: None | Queue = None
    _stderr_queue: None | Queue = None
    _original_stdout : None | Any = None
    _original_stderr : None | Any = None
    _started: bool = False

    @classmethod
    def ensure_activate(cls) -> None:
        """This must be called in the main thread.
        """
        if cls._started:
            return
        cls._activate()


    @classmethod
    def deactivate(cls):
        """
        NOTE: that this function is not intended to be called in normal cases. 
        The belwo are the creator's role

        * Not to use the `queue`
        * Not to use the addtional 
        """
        cls._started = False
        assert cls._timer_taskname is not None
        TimerTask.deregister(cls._timer_taskname)

        sys.stdout = cls._original_stdout
        sys.stderr = cls._original_stderr

    @classmethod
    def _activate(cls):
        cls._original_stdout = sys.stdout
        cls._original_stderr = sys.stderr

        cls._stdout_queue = cls._stdout_queue if cls._stdout_queue else Queue(maxsize=2 ** 20)
        cls._stderr_queue = cls._stderr_queue if cls._stderr_queue else Queue(maxsize=2 ** 20)
        cls._assure_empty_queue(cls._stdout_queue)
        cls._assure_empty_queue(cls._stderr_queue)

        sys.stdout = _DummyPipe(cls._stdout_queue)
        sys.stderr = _DummyPipe(cls._stderr_queue)

        cls._timer_taskname = TimerTask.register(cls.loop_function, interval=500, repeat=-1)
        cls._started = True

    @classmethod
    def _assure_empty_queue(cls, queue: Queue):
        while not queue.empty():
            try:
                queue.get_nowait()
            except Empty:
                break

    @classmethod
    def _fetch_text(cls, queue: Queue):
        text = ""
        while True:
            try:
                part = queue.get_nowait()
            except Empty:
                break
            text += part
        return text

    @classmethod
    def _output_stdout(cls):
        text = ""
        # [NOTE]: I would like to use `Exception`.
        # If we use Exectpion it is almost impossible to check from neovim.
        # So message is used.
        if cls._stdout_queue is None:
            text += "Crucial implementaiont Error in StdoutProxy. (StdoutQueue)\n"
        if not cls._original_stdout:
            text += "Crucial implementaiont Error in StdoutProxy. (original_stdout)\n"
        if cls._stdout_queue:
            text += cls._fetch_text(cls._stdout_queue)
        # If empty, it should not be called. 
        # It breaks! 

        cls._vim_message(text, level="ErrorMsg", with_echo=True)


        #if text:
        #    print(text, file=cls._original_stdout)
        # The below is not appropriate because other library may patch `sys.stdout`.
        # print(text, file=sys.__stdout__),
        # for the case where other library patch `sys.stdout`
        # Unfortunately, this way of thinking does not solve the problem, 
        # so `_vim_message` is introduced. 

    @classmethod
    def _output_stderr(cls):
        text = ""
        # [NOTE]: I woud like to use `Exception`.
        # However, if we use Exectpion it is almost impossible to check from neovim.
        # So message is used.
        if cls._stderr_queue is None:
            text += "Crucial implementaiont Error in StdoutProxy. (StderrQueue)\n"
        if not cls._original_stderr:
            text += "Crucial implementaiont Error in StdoutProxy. (original_stderr)\n"
        if cls._stderr_queue:
            text += cls._fetch_text(cls._stderr_queue)
        # If empty, the below should not be called. It raises Exception!
        cls._vim_message(text, level=None, with_echo=True)
        #print(text, file=cls._original_stderr)
        # The below is not appropriate because other library may patch `sys.stdout`.
        # print(text, sys.__stdout__) For the case where other library patch `sys.stdout`
        # Especially, in vim case, `vim` seems to patch `sys.__original__stderr`.
        # [ADD]: (2026/01/02): `print` does not seem to work in (VSCode+neovim) well, 
        # # So, I introduced `_vim_message`.  

    @classmethod
    def _vim_message(cls, text: str, level: Literal["ErrorMsg"] | None = None, with_echo: bool = True) -> None:
        if not text:
            return
        if level:
            vim.command(f"echohl {level}")

        for line in text.splitlines():
            safe = line.replace("'", "''")
            try:
                vim.command(f"echom '{safe}'")
            except Exception:
                vim.command("echom 'UnknownLine'")
        if level:
            vim.command("echohl None")

        if with_echo:
            text = text.replace("'", "''")
            try:
                vim.command(f"echo '{text}'")
            except Exception:
                vim.command("echo 'UnknownLine'")
        else:
            vim.command("echo '[echom] is used. See `:messages`. '")


    @classmethod
    def loop_function(cls):
        cls._output_stdout()
        cls._output_stderr()