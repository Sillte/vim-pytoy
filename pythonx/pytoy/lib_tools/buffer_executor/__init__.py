from pathlib import Path
from typing import Optional, Callable, Any, Mapping, Sequence, Annotated
from pytoy.ui import PytoyQuickFix, handle_records, QuickFixRecord

from pytoy.ui import PytoyBuffer

from pytoy.lib_tools.buffer_executor.command_wrapper import (
    CommandWrapper,
    naive_command_wrapper,
)
from pytoy.lib_tools.buffer_executor.buffer_job import (
    make_buffer_job,
    BufferJobProtocol,
)

from pytoy.lib_tools.utils import get_current_directory

from pytoy.lib_tools.buffer_executor.buffer_job_manager import BufferJobManager
from pytoy.lib_tools.buffer_executor.buffer_job_manager import BufferJobCreationParam, OnClosedCallable


from pytoy.ui.pytoy_buffer import make_buffer, make_duo_buffers

from pytoy.ui.pytoy_quickfix import to_quickfix_creator, QuickFixCreator

from pytoy.lib_tools.environment_manager import EnvironmentManager


class BufferExecutor:
    def __init__(self, job_name: str,  stdout: str | PytoyBuffer, stderr: str | PytoyBuffer | None = None):
        self._job_name = job_name
        
        if isinstance(stdout, str):
            if isinstance(stderr, PytoyBuffer):
                msg = "Combination of (`str, `PytoyBuffer`) is unacceptable. "
                raise ValueError(msg)
            if isinstance(stderr, str):
                stdout, stderr = make_duo_buffers(stdout, stderr)
            else:
                stdout = make_buffer(stdout)
        else:
            if isinstance(stderr, str):
                stderr = make_buffer(stderr)

        if stdout:
            stdout.init_buffer()
        if stderr:
            stderr.init_buffer()

        self._stdout: PytoyBuffer = stdout
        self._stderr: PytoyBuffer | None = stderr
        
    @property
    def job_name(self) -> str:
        return self._job_name
        
    @property  
    def stdout(self) -> PytoyBuffer:
        return self._stdout
        
    @property
    def stderr(self) -> PytoyBuffer | None:
        return self._stderr
    
    def run(self, command: str,
                  quickfix_creator: QuickFixCreator | None = None,  
                  cwd: str | Path | None = None,
                  command_wrapper: CommandWrapper | None = None,
                   *, env: Mapping[str, str] | None = None, 
                   on_closed: OnClosedCallable | None = None) -> None: 
        if command_wrapper is None:
            command_wrapper = EnvironmentManager().get_command_wrapper()
        if cwd is None:
            cwd = get_current_directory()

        wrapped_command = command_wrapper(command)

        stderr = self.stderr or self.stdout
        
        if isinstance(quickfix_creator, str):
            quickfix_creator  = to_quickfix_creator(quickfix_creator)
            
        def wrapped_on_closed(buffer_job: BufferJobProtocol) -> None:
            err_buffer = buffer_job.stderr or buffer_job.stdout 
            if not err_buffer:
                print("Illegal Path.")
                return 
            content = err_buffer.content
            if quickfix_creator:
                records = quickfix_creator(content)
                handle_records(
                    PytoyQuickFix(cwd=buffer_job.cwd), records=records, win_id=None, is_open=False
                )
            if on_closed:
                on_closed(buffer_job)
        
        param = BufferJobCreationParam(command=wrapped_command,
                               stdout=self.stdout,
                               stderr=stderr,
                               cwd=cwd,
                               env=env,
                               on_closed=wrapped_on_closed)
        self.stdout.append(wrapped_command)
        BufferJobManager.create(self.job_name, param)

    def sync_run(self, command: str,
                       cwd: str | Path | None = None,
                       command_wrapper: CommandWrapper | None = None,
                   *, env: Mapping[str, str] | None = None) -> None:
        import subprocess
        if cwd is None:
            cwd = get_current_directory()
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            text=True,
        )
        self.stdout.append(result.stdout)