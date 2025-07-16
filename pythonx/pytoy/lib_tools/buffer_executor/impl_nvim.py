import vim
import time
from queue import Queue
from pytoy.infra.timertask import TimerTask

from pathlib import Path
from typing import Callable

from pytoy.infra.vim_function import PytoyVimFunctions

from pytoy.ui import PytoyBuffer
from pytoy.ui.pytoy_buffer.queue_updater import QueueUpdater
from pytoy.lib_tools.buffer_executor.protocol import BufferJobProtocol


class NVimBufferJob(BufferJobProtocol):
    def __init__(
        self,
        name: str,
        stdout: PytoyBuffer | None = None,
        stderr: PytoyBuffer | None = None,
        *,
        env=None,
        cwd=None,
    ):
        self.name = name
        self._stdout = stdout
        self._stderr = stderr
        self.env = env
        self.cwd = cwd


    @property
    def stdout(self) -> PytoyBuffer | None:
        return self._stdout

    @property
    def stderr(self) -> PytoyBuffer | None:
        return self._stderr

    def job_start(
        self, command: str, on_start_callable: Callable, on_closed_callable: Callable
    ) -> None:

        def _make_buffer_handler(buffer: PytoyBuffer, suffix: str) -> NvimBufferHandler:
            queue = Queue()
            putter = NVimJobStartQueuePutter(f"{self.name}_{suffix}", queue)
            updater = QueueUpdater(buffer, queue)
            handler = NvimBufferHandler(putter, updater)
            return handler

        options = dict()

        if self.stdout:
            stdout_handler = _make_buffer_handler(self.stdout, "on_stdout")
            stdout_handler.register()
            options["on_stdout"] = stdout_handler.putter_vimfunc
        else:
            stdout_handler = None

        if self.stderr:
            stderr_handler = _make_buffer_handler(self.stderr, "on_stderr")
            stderr_handler.register()
            options["on_stderr"] = stderr_handler.putter_vimfunc
        else:
            stderr_handler = None


        if self.env is not None:
            options["env"] = self.env
        if self.cwd is not None:
            options["cwd"] = Path(self.cwd).as_posix()

        
        def wrapped_on_closed(*args):
            start = time.time()
            while time.time() - start < 0.5:
                if (not stdout_handler or stdout_handler.drained) and (
                    not stderr_handler or stderr_handler.drained
                ):
                    break

            if stdout_handler:
                stdout_handler.deregister()
            if stderr_handler:
                stderr_handler.deregister()
            on_closed_callable()
            vim.command(f"unlet g:{self.jobname}")
            # It is required to de-register this function in the different context.
            this_funcname = PytoyVimFunctions.to_vimfuncname(wrapped_on_closed)
            TimerTask.execute_oneshot(lambda: PytoyVimFunctions.deregister(this_funcname))

        # [NOTE]: `deregister` is performed inside `wrapped_on_closed`. 
        vimfunc_name = PytoyVimFunctions.register(wrapped_on_closed)
        options["on_exit"] = vimfunc_name

        prepared_dict = on_start_callable()
        if prepared_dict is None:
            prepared_dict = {}
        options.update(prepared_dict)

        # Register of `Job`.
        vim.command(f"let g:{self.jobname} = jobstart('{command}', {options})")

    @property
    def jobname(self) -> str:
        cls_name = self.__class__.__name__
        return f"__{cls_name}_{self.name}"

    @property
    def is_running(self):
        if int(vim.eval(f"exists('g:{self.jobname}')")):
            return True
        return False

    def stop(self):
        """Stop `Executor`."""
        if int(vim.eval(f"exists('g:{self.jobname}')")):
            vim.command(f":call jobstop(g:{self.jobname})")
        else:
            print(f"Already, `{self.jobname}` is stopped.")


class NVimJobStartQueuePutter:
    VIMFUNCTION_SUFFIX = "_nvim_jobstart_putter"

    def __init__(self, name: str, queue: Queue):
        self._name = name
        self._queue = queue
        self._drained: bool = True
        self._vim_function: str | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def vim_function(self) -> str | None:
        return self._vim_function

    @property
    def drained(self):
        return self._drained

    def register(self) -> str:
        """Register the putting job.``"""
        buffer = ""
        def _on_stdout(job_id, data, event):
            nonlocal buffer
            if data:
                data[0] = buffer + data[0]
                lines = [line.strip("\r") for line in data[:-1]]
                self._queue.put(lines)
                buffer = data[-1]
            if (not data) or (len(data) == 1 and bool(data[0]) is False):
                self._drained = True
            else:
                self._drained = False
            _ = job_id = event

        self._drained = True
        vimfuncname = PytoyVimFunctions.register(
            _on_stdout, name=f"{self.name}_{self.VIMFUNCTION_SUFFIX}"
        )
        self._vim_function = vimfuncname
        return self._vim_function

    def deregister(self):
        if not self.vim_function:
            raise ValueError("`NVimJobStartQueuePutter is not yet registered.`")
        PytoyVimFunctions.deregister(self.vim_function)



class NvimBufferHandler:
    def __init__(
        self, queue_putter: NVimJobStartQueuePutter, queue_updater: QueueUpdater
    ):
        self._putter = queue_putter
        self._updater = queue_updater

        self._putter_vimfunc: str | None = None
        self._updater_taskname: str | None = None

    @property
    def drained(self) -> bool:
        return self._putter.drained

    @property
    def putter_vimfunc(self) -> str | None:
        return self._putter_vimfunc

    @property
    def updater_taskname(self) -> str | None:
        return self._updater_taskname

    def register(self) -> tuple[str, str]:
        self._putter_vimfunc = self._putter.register()
        self._updater_taskname = self._updater.register()
        return (self._putter_vimfunc, self._updater_taskname)

    def deregister(self):
        self._putter.deregister()
        self._updater.deregister()
