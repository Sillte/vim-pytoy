import vim
from typing import Optional, Dict

from pytoy.ui_utils import to_buffer_number, store_window
from pytoy.func_utils import PytoyVimFunctions, with_return


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

    @property
    def name(self):
        return self._name

    @property
    def stdout(self) -> Optional["Buffer"]:
        return self._stdout

    @property
    def stderr(self) -> Optional["Buffer"]:
        return self._stderr

    @property
    def command(self) -> str:
        return self._command

    @property
    def jobname(self) -> str:
        cls_name = self.__class__.__name__
        return f"__{cls_name}_{self.name}"

    def run(self, command: "str", stdout: "Buffer", stderr: Optional["Buffer"] = None):
        """Run the `command`.

        Args:
            command: `str`:
        """
        self._command = command
        self._stdout = stdout
        self._stderr = stderr

        options = dict()
        if self.stdout is not None:
            options["out_io"] = "buffer"
            options["out_buf"] = self.stdout.number

        if self.stderr is not None:
            options["err_io"] = "buffer"
            options["err_buf"] = self.stderr.number

        options = self._flow_on_preparation(options)

        if not isinstance(command, str):
            command = " ".join(command)
        # Register of `Job`.
        vim.command(f"let g:{self.jobname} = job_start('{command}', {options})")

    @property
    def is_running(self):
        """Return whether"""
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

    def prepare(self) -> Dict:
        """Prepare setting of `options` and others.

        * You can modify the options of `job-options` here.
        * You must not have the `key` of `exit_cb`.
            - you should use `on_closed` for the processings to this key.

        * https://vim-jp.org/vimdoc-ja/channel.html#job-options
        """
        return {}

    def on_closed(self):
        """Function when the terminal ends.
        Typically, the processing of the output result is performed.
        """
        pass

    def _flow_on_preparation(self, options) -> Dict:
        """Flow at just before `run`."""
        vimfunc_name = PytoyVimFunctions.register(
            self._flow_on_closed, prefix=f"{self.jobname}_VIMFUNC"
        )
        options["exit_cb"] = vimfunc_name

        prepared_dict = self.prepare()
        if prepared_dict is None:
            prepared_dict = {}
        options.update(prepared_dict)
        return options

    def _flow_on_closed(self):
        """Perform the processings when the execution is finished.

        1. User-defined closing function (`self.on_closed`) is performed.
        2. De-register of the `job` is performed.
        """
        self.on_closed()
        # de-register of Job.
        vim.command(f"unlet g:{self.jobname}")
