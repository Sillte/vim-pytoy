import vim
from threading import Thread
from queue import Queue
from queue import Empty
from pytoy.timertask_manager import TimerTaskManager


from pathlib import Path
from typing import Optional, Callable, Protocol

from pytoy.func_utils import PytoyVimFunctions

from pytoy.ui_pytoy import PytoyBuffer

from pytoy.executors.command_wrapper import CommandWrapper
from pytoy.executors.buffer_job import BufferJobProtocol, VimBufferJob, NVimBufferJob

naive_wrapper = CommandWrapper()


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
    def stdout(self) -> Optional[PytoyBuffer]:
        if not self._buffer_job:
            return None
        return self._buffer_job.stdout

    @property
    def stderr(self) -> Optional[PytoyBuffer]:
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
        stdout: Optional[PytoyBuffer] = None,
        stderr: Optional[PytoyBuffer] = None,
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

        if stdout is not None:
            stdout.init_buffer(command)
        if stderr is not None:
            stderr.init_buffer()

        if self.is_running:
            raise ValueError(f"`{self.name=}` is already running")
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
