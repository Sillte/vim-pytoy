import vim

class BufferExecutor:
    """ Execute `command` with output `stdout`, `stderr` buffers. 

    Args:
        name(str): Specifier of `Executor`. It should be valid as the variable of vim script.
    """
    __cache = dict()
    def __new__(cls, name):
        if name in cls.__cache:
            return cls.__cache[name]
        self = object.__new__(cls)
        return self

    def __init__(self, name):
        self.name = name

    @property
    def jobname(self):
        return f"__BufferExecutor_{self.name}"

    def run(self, command, stdout, stderr):
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        self.win_id = vim.eval("win_getid()")


        options = {"out_io": "buffer",
                   "out_buf": self.stdout.number,
                   "err_io": "buffer",
                   "err_buf": self.stderr.number}

        self.prepare(options)
        if not isinstance(command, str):
            command = " ".join(command)
        # Register of `Job`.
        vim.command(f"let g:{self.jobname} = job_start('{command}', {options})")

    @property
    def is_running(self):
        if not int(vim.eval(f"exists('g:{self.jobname}')")):
            return False
        status = vim.eval(f"job_status(g:{self.jobname})")
        return status == "run"

    def stop(self):
        """Stop `Executor`.
        """
        if int(vim.eval(f"exists('g:{self.jobname}')")):
            vim.command(f":call job_stop(g:{self.jobname})")
        else:
            print(f"Already, `{self.jobname}` is stopped.")

    def prepare(self, options) -> None:
        """Prepare setting of `options` and others.

        You can modify this in order to add or revise options.

        Sample of Callback.
        ------------------------
        ```
        def prepare(self, options):
            vimfunc_name = PytoyVimFunctions.register(f"{self.jobname}_on_closed", self.on_closed)
            options["exit_cb"] = vimfunc_name
        ...
        def on_closed(self):
            args = vim.eval("a:000")
            # hogehoge.
        ```
        """
        pass

