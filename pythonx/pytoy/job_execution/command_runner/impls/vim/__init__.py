from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping

import vim

from pytoy.job_execution.command_runner.domain.models import (
    OutputJobRequest,
    SpawnOption,
)
from pytoy.job_execution.command_runner.domain.protocol import JobEvents, JobID, OutputJobProtocol, Snapshot
from pytoy.job_execution.command_runner.impls.core import OutputJobCore
from pytoy.job_execution.process_utils import find_children_pids
from pytoy.shared.lib.function import FunctionRegistry
from pytoy.shared.timertask import TimerTask


class OutputJobVim(OutputJobProtocol):
    def __init__(self, job_request: OutputJobRequest, spawn_option: SpawnOption):
        self._name = job_request.name
        self._core = OutputJobCore(self._name)

        # _build events.
        self._start_caller = self._build_start_impl(job_request, spawn_option)

    def _build_start_impl(self, job_request: OutputJobRequest, spawn_option: SpawnOption) -> Callable[[], None]:

        self._jobvar = f"pytoy_output_job_{id(self)}"
        if not (cwd := spawn_option.cwd):
            cwd = Path().cwd()
        self._cwd = Path(cwd)
        on_out = FunctionRegistry.register(lambda _, line: self._core.emit_stdout(line), prefix="OutputJobOut")
        on_err = FunctionRegistry.register(lambda _, line: self._core.emit_stderr(line), prefix="OutputJobErr")
        on_exit = FunctionRegistry.register(
            lambda _, status: self._core.emit_exit(self, status), prefix="OutputJobExit"
        )

        vim_funcs = [on_out, on_err, on_exit]

        def _construct_option(
            job_request: OutputJobRequest, spawn_option: SpawnOption, cwd: Path
        ) -> dict[str, str | Mapping[str, str]]:
            option: dict[str, str | Mapping[str, str]] = {
                "exit_cb": on_exit.impl_name,
                "mode": "nl",  # 行単位
            }

            output_requests = set(job_request.outputs)

            if "stdout" in output_requests:
                option["out_cb"] = on_out.impl_name

            if "stderr" in output_requests:
                option["err_cb"] = on_err.impl_name

            option["cwd"] = cwd.absolute().as_posix()

            if env := spawn_option.env:
                option["env"] = env
            return option

        def _cleanup():
            for f in vim_funcs:
                FunctionRegistry.deregister(f)
            vim.command(f"silent! unlet g:{self._jobvar}")
            self.dispose()

        self._disposables = []
        self._disposables.append(
            self.events.on_job_exit.subscribe(lambda _: TimerTask.execute_oneshot(_cleanup, interval=0))
        )
        option = _construct_option(job_request=job_request, spawn_option=spawn_option, cwd=self._cwd)

        self._disposables.append(
            self.events.on_job_exit.subscribe(lambda _: vim.command(f"silent! unlet g:{self._jobvar}"))
        )

        def start_impl() -> None:
            vim.command(f"let g:{self._jobvar} = job_start({json.dumps(job_request.command)}, {json.dumps(option)})")
            debug_status = vim.eval(f"job_status(g:{self._jobvar})")
            if debug_status == "fail":
                raise ValueError(
                    f"Failed to execute the command, `{job_request.command=}`, {option=}",
                )

        return start_impl

    def start(self) -> None:
        if self.alive:
            raise RuntimeError("Output Jos is already started.")
        self._start_caller()

    @property
    def cwd(self) -> Path:
        return Path(self._cwd)

    @property
    def pid(self) -> int:
        # Retrieve PID from job info
        try:
            return int(vim.eval(f"job_info(g:{self._jobvar}).process"))
        except Exception:
            return -1

    @property
    def children_pids(self) -> list[int]:
        return find_children_pids(self.pid)

    @property
    def job_id(self) -> JobID:
        return self._jobvar

    @property
    def name(self) -> str:
        return self._name

    @property
    def events(self) -> JobEvents:
        return self._core.events

    @property
    def alive(self) -> bool:
        try:
            status = vim.eval(f"job_status(g:{self._jobvar})")
        except Exception:
            return False
        return status == "run"

    def terminate(self) -> None:
        """Requires idempotency."""
        if self.alive:
            try:
                vim.command(f"call job_stop(g:{self._jobvar})")
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
