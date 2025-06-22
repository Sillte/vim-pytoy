import vim
import time
from queue import Queue
from queue import Empty
from pytoy.timertask_manager import TimerTaskManager

from pathlib import Path
from typing import Callable, Protocol

from pytoy.func_utils import PytoyVimFunctions

from pytoy.ui_pytoy import PytoyBuffer
from pytoy.buffer_executor.command_wrapper import CommandWrapper


naive_wrapper = CommandWrapper()


class BufferJobProtocol(Protocol):
    def __init__(
        self,
        name: str,
        stdout=PytoyBuffer | None,
        stderr=PytoyBuffer | None,
        *,
        env=None,
        cwd=None,
    ):
        ...

    def job_start(
        self, command: str, on_start_callable: Callable, on_closed_callable: Callable
    ) -> None:
        ...

    @property
    def is_running(self) -> bool:
        ...

    def stop(self) -> None:
        ...


class NVimBufferJob(BufferJobProtocol):
    def __init__(
        self,
        name: str,
        stdout=PytoyBuffer | None,
        stderr=PytoyBuffer | None,
        *,
        env=None,
        cwd=None,
    ):
        self.name = name
        self.stdout = stdout
        self.stderr = stderr
        self.env = env
        self.cwd = cwd

        self._on_stdout_name = None
        self._on_stderr_name = None

    def job_start(
        self, command: str, on_start_callable: Callable, on_closed_callable: Callable
    ) -> None:
        options = dict()

        stdout_drained = True
        if self.stdout is not None:
            stdout_queue = Queue()
            stdout_drained = False

            def _on_stdout(job_id, data, event):
                nonlocal stdout_drained
                stdout_queue.put(data)
                if (not data) or (len(data) == 1 and bool(data[0]) is False):
                    stdout_drained = True
                else:
                    stdout_drained = False
                _ = job_id = event

            self._on_stdout_name = PytoyVimFunctions.register(
                _on_stdout, f"{self.name}_on_stdout"
            )
            options["on_stdout"] = self._on_stdout_name

            def _update_stdout():
                while stdout_queue.qsize():
                    try:
                        lines = stdout_queue.get_nowait()
                        for line in lines:
                            line = line.strip("\r")
                            self.stdout.append(line) # type: ignore
                    except Empty:
                        break

            TimerTaskManager.register(_update_stdout, name=self._on_stdout_name)

        stderr_drained = True
        if self.stderr is not None:
            stderr_drained = False
            stderr_queue = Queue()

            def _on_stderr(job_id, data, event):
                nonlocal stderr_drained
                _ = job_id = event
                stderr_queue.put(data)
                if (not data) or (len(data) == 1 and bool(data[0]) is False):
                    stderr_drained = True
                else:
                    stderr_drained = False

            self._on_stderr_name = PytoyVimFunctions.register(
                _on_stderr, f"{self.name}_on_stderr"
            )
            options["on_stderr"] = self._on_stderr_name

            def _update_stderr():
                assert self.stderr is not None
                while stderr_queue.qsize():
                    try:
                        lines = stderr_queue.get_nowait()
                        for line in lines:
                            line = line.strip("\r")
                            self.stderr.append(line) # type: ignore
                    except Empty:
                        break

            TimerTaskManager.register(_update_stderr, name=self._on_stderr_name)

        if self.env is not None:
            options["env"] = self.env
        if self.cwd is not None:
            options["cwd"] = Path(self.cwd).as_posix()

        def wrapped_on_closed(*args):
            start = time.time()
            nonlocal stdout_drained
            nonlocal stderr_drained
            while time.time() - start < 0.5:
                if stdout_drained and stderr_drained:
                    break
            if self.stdout:
                _update_stdout()
                TimerTaskManager.deregister(self._on_stdout_name) 
                self._on_stdout_name = None
            if self.stderr:
                _update_stderr()
                TimerTaskManager.deregister(self._on_stderr_name)
                self._on_stderr_name = None
            on_closed_callable()
            vim.command(f"unlet g:{self.jobname}")

        vimfunc_name = PytoyVimFunctions.register(
            wrapped_on_closed, prefix=f"{self.jobname}_VIMFUNC"
        )
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


class VimBufferJob(BufferJobProtocol):
    def __init__(
        self,
        name: str,
        stdout: None | PytoyBuffer = None,
        stderr: None | PytoyBuffer = None,
        *,
        env=None,
        cwd=None,
    ):
        self.name = name
        self.stdout = stdout
        self.stderr = stderr
        self.env = env
        self.cwd = cwd

    def job_start(
        self, command: str, on_start_callable: Callable, on_closed_callable: Callable
    ):
        options = dict()
        if self.stdout is not None:
            options["out_io"] = "buffer"
            options["out_buf"] = self.stdout.identifier

        if self.stderr is not None:
            options["err_io"] = "buffer"
            options["err_buf"] = self.stderr.identifier

        if self.env is not None:
            options["env"] = self.env
        if self.cwd is not None:
            options["cwd"] = Path(self.cwd).as_posix()

        def wrapped_on_closed():
            on_closed_callable()
            vim.command(f"unlet g:{self.jobname}")

        vimfunc_name = PytoyVimFunctions.register(
            wrapped_on_closed, prefix=f"{self.jobname}_VIMFUNC"
        )
        options["exit_cb"] = vimfunc_name

        prepared_dict = on_start_callable()
        if prepared_dict is None:
            prepared_dict = {}
        options.update(prepared_dict)

        # Register of `Job`.
        vim.command(f"let g:{self.jobname} = job_start('{command}', {options})")

    @property
    def jobname(self) -> str:
        cls_name = self.__class__.__name__
        return f"__{cls_name}_{self.name}"

    @property
    def is_running(self):
        if not int(vim.eval(f"exists('g:{self.jobname}')")):
            return False
        status = vim.eval(f"job_status(g:{self.jobname})")
        return status == "run"

    def stop(self):
        """Stop `Executor`."""
        if int(vim.eval(f"exists('g:{self.jobname}')")):
            vim.command(f":call job_stop(g:{self.jobname})")
        else:
            print(f"Already, `{self.jobname}` is stopped.")


if __name__ == "__main__":
    pass
