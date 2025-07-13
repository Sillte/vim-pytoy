from pathlib import Path
from typing import Callable

import vim

from pytoy.infra.vim_function import PytoyVimFunctions

from pytoy.ui import PytoyBuffer
from pytoy.lib_tools.buffer_executor.protocol import BufferJobProtocol


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
    ):
        from pytoy.ui.pytoy_buffer.impl_vim import PytoyBufferVim
        options = dict()
        if self.stdout is not None:
            options["out_io"] = "buffer"
            impl = self.stdout.impl
            assert isinstance(impl,  PytoyBufferVim)
            options["out_buf"] = impl.buffer.number

        if self.stderr is not None:
            options["err_io"] = "buffer"
            impl = self.stderr.impl
            assert isinstance(impl,  PytoyBufferVim)
            options["err_buf"] = impl.buffer.number

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
