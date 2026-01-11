from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping, Any, TYPE_CHECKING

from pytoy.lib_tools.command_runner.models import OutputJobProtocol, OutputJobRequest, SpawnOption, JobEvents, JobID
from pytoy.ui.ui_enum import get_ui_enum, UIEnum
from pytoy.ui import PytoyBuffer
from pytoy.ui.pytoy_buffer import make_buffer, make_duo_buffers
if TYPE_CHECKING:
    from pytoy.contexts.pytoy import GlobalPytoyContext

def _solve_buffers(stdout: PytoyBuffer | str, stderr: PytoyBuffer| str | None):
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
    return stdout, stderr 


def make_output_job(job_request: OutputJobRequest, spawn_option: SpawnOption) -> OutputJobProtocol:
    ui_enum = get_ui_enum()
    if ui_enum == UIEnum.VIM:
        from pytoy.lib_tools.command_runner.impls.vim import OutputJobVim
        return OutputJobVim(job_request, spawn_option)
    elif ui_enum in {UIEnum.NVIM, UIEnum.VSCODE}:
        from pytoy.lib_tools.command_runner.impls.nvim import OutputJobNvim
        return OutputJobNvim(job_request, spawn_option)
    else:
        raise RuntimeError(f"Unsupported UI: {ui_enum}")
        

class CommandRunner:
    @classmethod
    def solve_buffers(cls, stdout: PytoyBuffer | str, 
                           stderr: PytoyBuffer| str | None = None) -> tuple[PytoyBuffer, PytoyBuffer | None]:
        return _solve_buffers(stdout, stderr)


    def __init__(self, stdout: PytoyBuffer | str,
                       stderr: PytoyBuffer| str | None = None,
                         *,
                       init_buffer: bool = True,
                       output_job_factory: Callable[..., OutputJobProtocol] = make_output_job, 
                       ctx:  GlobalPytoyContext | None = None ) -> None:
        stdout, stderr =  self.solve_buffers(stdout, stderr)
        if init_buffer:
            stdout.init_buffer()
            if stderr:
                stderr.init_buffer()
        self._stdout = stdout
        self._stderr = stderr
        self._output_job_factory = output_job_factory
        self._output_job: OutputJobProtocol | None  = None
        
    @property
    def stdout(self) -> PytoyBuffer:
        return self._stdout

    @property
    def stderr(self) -> PytoyBuffer | None:
        return self._stdout

        
    def _wire_events(self, request: OutputJobRequest, job_events: JobEvents):
        disposables = []
        d_out = job_events.on_update_stdout_line.subscribe(self._update_stdout)
        stdout_events = self._stdout.events
        d_out_wiped = stdout_events.on_wiped.subscribe(lambda _: d_out.dispose())
        disposables += [d_out, d_out_wiped]
        if self._stderr and self._stderr is not self._stdout:
            d_err = job_events.on_update_stderr_line.subscribe(
                self._update_stderr if self._stderr else self._update_stdout
            )
            d_err_wiped = stdout_events.on_wiped.subscribe(lambda _: d_err.dispose())
            disposables += [d_err, d_err_wiped]
        disposables.append(
            job_events.on_job_exit.subscribe(lambda _: self._dispose_job())
        )
        if request.on_exit:
            disposables.append(job_events.on_job_exit.subscribe(request.on_exit))
        return disposables
    
    @property
    def events(self) -> JobEvents:
        if not self._output_job:
            msg = "Until `run` is invoked, `events` cannot be accessed. "
            raise RuntimeError(msg)
        return self._output_job.events

    @property
    def job_id(self) -> JobID:
        if not self._output_job:
            msg = "Until `run` is invoked, `job_id` cannot be accessed. "
            raise RuntimeError(msg)
        return self._output_job.job_id

    def run(
        self,
        request: OutputJobRequest,
        spawn_option: SpawnOption | None = None,
    ) -> JobID:
        if self._output_job:
            raise RuntimeError("Runner already running.")

        spawn_option = spawn_option if spawn_option else SpawnOption()
        self._output_job = self._output_job_factory(request, spawn_option)
        self._job_disposables = []
        self._job_disposables += self._wire_events(request, self._output_job.events)
        return self._output_job.job_id
    
    def _dispose_job(self, ):  
        """Dispose the disposable related to `output_job`. 
        """
        if self._output_job and self._output_job.alive:
            self._output_job.terminate()

        for d in self._job_disposables:
            d.dispose()
        self._job_disposables.clear()
        self._output_job = None

    def dispose(self) -> None:
        self._dispose_job()
     

    @property
    def alive(self) -> bool:
        if not self._output_job:
            return False
        return self._output_job.alive

    def terminate(self) -> None:
        if not self._output_job:
            # Already`job` is done. 
            print("Currently, No OutputJobs are running.")
            return 
        self._output_job.terminate()
                
    def _update_stdout(self, line: str): 
        try:
            self._stdout.append(line)
        except Exception as e:
            pass

    def _update_stderr(self, line: str): 
        try:
            assert self._stderr
            self._stderr.append(line)
        except Exception as e:
            pass
        


if __name__ == "__main__":
    #request = OutputJobRequest(command=["cmd",  "/c", 'echo helloAAA...'], on_exit=lambda _: print(str(_)))
    #stdout = "MOCK_OUT"
    #runner = BufferRunner(request, stdout)

    # テスト用のリクエスト
    request = OutputJobRequest(
    command=["python", "-c", "import time; [print(f'Count {i}', flush=True) or time.sleep(1) for i in range(10)]"],
    name="LongTask",
    on_exit=lambda job: print(f"\n[Finalized] Job ID: {job.job_id} finished.")
)
    # 実行
    runner = CommandRunner( "TEST_BUFFER")
    runner.run(request)

    import time  
    print(runner.alive)
    time.sleep(0.4)
    #runner.terminate()
    #time.sleep(0.4)
    #print(runner.alive)


