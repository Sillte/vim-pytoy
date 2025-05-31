import vim
from threading import Thread
from queue import Queue
from queue import Empty
from pytoy.timertask_manager import TimerTaskManager


from pathlib import Path
from typing import Optional, Callable, Protocol

from pytoy.func_utils import PytoyVimFunctions


class CommandWrapper:
    """Callable. modify the command you execute.
    Sometimes, we would like to change the environment
    where the command is executed.
    * not naive python, but the python of virtual environment.
    * not naive invocation, but with `uv run`.
    `CommandWrapper` handles this kind of request with depndency injection.
    """

    def __call__(self, cmd: str) -> str:
        return cmd


naive_wrapper = CommandWrapper()


class BufferJobProtocol(Protocol):
    def __init__(self, name: str, stdout=None, stderr=None, *, env=None, cwd=None):
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
    def __init__(self, name: str, stdout=None, stderr=None, *, env=None, cwd=None):
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
        if self.stdout is not None:
            # options["out_io"] = "buffer"
            # options["out_buf"] = self.stdout.number
            stdout_queue = Queue()

            def _on_stdout(job_id, data, event):
                _ = job_id = event
                stdout_queue.put(data)

            self._on_stdout_name = PytoyVimFunctions.register(
                _on_stdout, f"{self.name}_on_stdout"
            )
            options["on_stdout"] = self._on_stdout_name

            def _update():
                while stdout_queue.qsize():
                    try:
                        lines = stdout_queue.get_nowait()
                        self.stdout.append(lines)
                    except Empty:
                        break

            TimerTaskManager.register(_update, name=self._on_stdout_name)

        if self.stderr is not None:
            stderr_queue = Queue()

            def _on_stderr(job_id, data, event):
                _ = job_id = event
                stderr_queue.put(data)

            self._on_stderr_name = PytoyVimFunctions.register(
                _on_stderr, f"{self.name}_on_stderr"
            )
            options["on_stderr"] = self._on_stderr_name

            def _update():
                while stderr_queue.qsize():
                    try:
                        lines = stderr_queue.get_nowait()
                        self.stderr.append(lines)
                    except Empty:
                        break

            TimerTaskManager.register(_update, name=self._on_stderr_name)

        if self.env is not None:
            options["env"] = self.env
        if self.cwd is not None:
            options["cwd"] = Path(self.cwd).as_posix()

        def wrapped_on_closed():
            on_closed_callable()
            if self.stdout:
                TimerTaskManager.deregister(self._on_stdout_name)
                self._on_stdout_name = None
            if self.stderr:
                TimerTaskManager.deregister(self._on_stderr_name)
                self._on_stderr_name = None
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
    def __init__(self, name: str, stdout=None, stderr=None, *, env=None, cwd=None):
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
            options["out_buf"] = self.stdout.number

        if self.stderr is not None:
            options["err_io"] = "buffer"
            options["err_buf"] = self.stderr.number

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


class BufferExecutor:
    """Execute `command` with output `stdout`, `stderr` buffers.

    Guide for derivation and usage.
    ------------------------------------------
    Shortly, in many use-cases what you do is following 2 steps.

    1. Implement `on_closed` to apply processing to the output of `buffers` at the end of `job`.
    2. At invoking, call `self.run`.

    Additionally, if you would like to store state while execution,
    please use `self.prepare`.

    Implementation murmurs.
    ------------------------------------------

    * Registration of global variable is necessary to manage the state of running or stop.
    * `_flow_***` are introduced for performing both of the below.
        - 1). To register / de-register of `self.jobname`
        - 2). Execute user defined processing.
    """

    __cache = dict()

    def __new__(cls, name=None):
        if name is None:
            name = cls.__name__
        if name in cls.__cache:
            return cls.__cache[name]
        self = object.__new__(cls)
        self._init(name)
        cls.__cache[name] = self
        return self

    def _init(self, name):
        self._name = name
        self._stdout = None
        self._stderr = None
        self._command = None
        self._buffer_job = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def stdout(self) -> Optional["vim.buffer"]:
        if not self._buffer_job:
            return None
        return self._buffer_job.stdout

    @property
    def stderr(self) -> Optional["vim.buffer"]:
        if not self._buffer_job:
            return None
        return self._buffer_job.stderr

    @property
    def command(self) -> str | None:
        return self._command

    @property
    def buffer_job(self) -> BufferJobProtocol | None:
        if not self._buffer_job:
            return None
        return self._buffer_job

    def run(
        self,
        command: str | list[str],
        stdout: Optional["vim.buffer"] = None,
        stderr: Optional["vim.buffer"] = None,
        command_wrapper: Callable[[str], str] | None = naive_wrapper,
        *,
        env: dict[str, str] | None = None,
        cwd: str | Path | None = None,
    ):
        """Run the `command`.

        Args:
            command: `str`:
        """
        if not isinstance(command, str):
            command = " ".join(command)
        if command_wrapper is None:
            command_wrapper = naive_wrapper
        self._command = command

        if int(vim.eval("has('nvim')")):
            self._buffer_job = NVimBufferJob(
                name=self.name, stdout=stdout, stderr=stderr, env=env, cwd=cwd
            )

        else:
            self._buffer_job = VimBufferJob(
                name=self.name, stdout=stdout, stderr=stderr, env=env, cwd=cwd
            )
        command = command_wrapper(command)
        self._buffer_job.job_start(command, self.prepare, self.on_closed)

    @property
    def is_running(self):
        """Return whether the job is running"""
        if not self.buffer_job:
            return False
        return self.buffer_job.is_running

    def stop(self):
        if not self.buffer_job:
            print(f"Already, stopped, {self.__class__}")
            return
        self.buffer_job.stop()

    def prepare(self) -> dict | None:
        """Prepare setting of `options` and others.

        * You can modify the options of `job-options` here.
        * You must not have the `key` of `exit_cb`.
            - you should use `on_closed` for the processings to this key.

        * https://vim-jp.org/vimdoc-ja/channel.html#job-options
        """
        return {}

    def on_closed(self) -> None:
        """Function when the terminal ends.
        Typically, the processing of the output result is performed.
        """
        pass


if __name__ == "__main__":
    pass
