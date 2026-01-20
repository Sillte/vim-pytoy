from __future__ import annotations 
import vim
from pytoy.lib_tools.command_runner.models import OutputJobRequest, SpawnOption, JobID, JobEvents, Snapshot, OutputJobProtocol
from pytoy.lib_tools.command_runner.impls.core import OutputJobCore
from pytoy.lib_tools.process_utils import  find_children_pids
from pytoy.infra.vim_function import VimFunctionName, PytoyVimFunctions
from pytoy.infra.timertask import TimerTask
from typing import TYPE_CHECKING, Any
from pathlib import Path

if TYPE_CHECKING:
    from pytoy.contexts.vim import GlobalVimContext


class OutputJobVim(OutputJobProtocol):
    def __init__(self, job_request: OutputJobRequest, spawn_option: SpawnOption, *, ctx: GlobalVimContext | None = None):
        self._name = job_request.name
        self._core = OutputJobCore(self._name)

        self._stdout_lines = []
        self._stderr_lines = []
        self._start(job_request, spawn_option)
        
    def _start(self, job_request: OutputJobRequest, spawn_option: SpawnOption):
        on_out = PytoyVimFunctions.register(lambda _, line: self._core.emit_stdout(line), prefix="OutputJobOut")
        on_err = PytoyVimFunctions.register(lambda _, line: self._core.emit_stderr(line), prefix="OutputJobErr")
        on_exit = PytoyVimFunctions.register(lambda _j, status: self._core.emit_exit(self, status), prefix="OutputJobExit")
        vim_funcs = [on_out, on_err, on_exit]

        def _cleanup():
            for f in vim_funcs:
                PytoyVimFunctions.deregister(f)
            vim.command(f"silent! unlet g:{self._jobid}")
            self.dispose()
        
        self._disposables = []
        self._disposables.append(self.events.on_job_exit.subscribe(lambda _ : TimerTask.execute_oneshot(_cleanup, interval=0)))
        

        output_requests = set(job_request.outputs)

        option = {
            "exit_cb": on_exit,
            "mode": "nl",  # 行単位
        }

        if "stdout" in output_requests:
            option["out_cb"] = on_out

        if "stderr" in output_requests:
            option["err_cb"] = on_err

        if not (cwd := spawn_option.cwd):
            cwd = Path().cwd()

        self._cwd = Path(cwd)
        option["cwd"] = self._cwd.absolute().as_posix()
        
        if (env := spawn_option.env):
            option["env"] = env # type: ignore

        import json
        self._jobid = f"{self._name}_{id(self)}"

        vim.command(f"let g:{self._jobid} = job_start({json.dumps(job_request.command)}, {json.dumps(option)})")
        self._disposables.append(self.events.on_job_exit.subscribe(lambda _: vim.command(f"silent! unlet g:{self._jobid}")))

        debug_status = vim.eval(f"job_status(g:{self._jobid})")
        if debug_status == "fail":
            raise ValueError(f"Failed to execute the command, `{job_request.command=}`, {option=}", )

    
    @property
    def cwd(self) -> Path:
        return Path(self._cwd)
        
    @property
    def pid(self) -> int:
        # Retrieve PID from job info
        try:
            return int(vim.eval(f"job_info(g:{self._jobid}).process"))
        except Exception:
            return -1

    @property
    def children_pids(self) -> list[int]:
        return find_children_pids(self.pid)

    @property
    def job_id(self) -> JobID:
        return self._jobid

    @property
    def name(self) -> str:
        return self._name

    @property
    def events(self) -> JobEvents:
        return self._core.events

    @property
    def alive(self) -> bool:
        try:
            status = vim.eval(f"job_status(g:{self._jobid})")
        except Exception:
            return False
        return status == "run"

    def terminate(self) -> None:
        """Requires idempotency."""
        if self.alive:
            try:
                vim.command(f"call job_stop(g:{self._jobid})")
            except Exception:
                pass

    def dispose(self) -> None:
        self.terminate()

        for d in self._disposables:
            d.dispose()
        self._core.dispose()

    @property
    def snapshot(self) -> Snapshot:
        # Return current captured lines
        return self._core.snapshot   
