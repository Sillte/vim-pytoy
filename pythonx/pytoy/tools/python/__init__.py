"""Exectuor for `Python`."""

import vim
import json
import re
from shlex import quote
from pathlib import  Path
from dataclasses import dataclass

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.lib_tools.command_executor import CommandExecutor, BufferRequest, ExecutionRequest, ExecutionHooks, ExecutionResult
from pytoy.lib_tools.command_executor import CommandExecutionManager, CommandExecution

# `set_default_execution_mode` is carried out only in `__init__.py`
from pytoy.lib_tools.utils import get_current_directory


from pytoy.ui import PytoyBuffer, PytoyQuickfix, handle_records, QuickfixRecord



class PythonExecutor():
    command_kind = "PythonExecutor"
    
    def __init__(self, *, execution_manager:  CommandExecutionManager | None = None):
        if not execution_manager:
            execution_manager = GlobalPytoyContext.get().command_execution_manager
        self.execution_manager = execution_manager


    def runfile(
        self,
        path: str | Path,
        stdout: PytoyBuffer,
        stderr: PytoyBuffer,
        *,
        cwd: Path | None=None,
        force_uv: bool = False,
    ):

        if cwd is None:
            cwd = get_current_directory()
        else:
            cwd = Path(cwd)
        command = " ".join(["python", "-u", "-X", "utf8", Path(path).as_posix()])
        def _append_command(execution: CommandExecution) -> None:
            execution.runner.stdout.append(str(execution.command))

        buffer_request = BufferRequest(stdout=stdout, stderr=stderr)
        executor = CommandExecutor(buffer_request)
        execution_req = ExecutionRequest(command, cwd=cwd, command_wrapper="uv" if force_uv else "auto")
        hooks = ExecutionHooks(on_finish=lambda res: self.on_closed(res, stderr=stderr, cwd=cwd),
                               on_start=_append_command)
        executor.execute(execution_req, hooks=hooks, kind=self.command_kind)


    def rerun(self, stdout, stderr, force_uv=None):
        """Execute the previous `path`."""
        last_context = self.execution_manager.get_last_context_by_kind(self.command_kind)
        if not last_context: 
            raise RuntimeError("Previous executions are not existent.")
        
        execution_req = last_context.execution_request
        cwd = execution_req.cwd
        if cwd is None:
            raise RuntimeError("Violation of `last_context`, `cwd` is None.")
        buffer_request = BufferRequest(stdout=stdout, stderr=stderr)
        executor = CommandExecutor(buffer_request)

        hooks = ExecutionHooks(on_finish=lambda res: self.on_closed(res, stderr=stderr, cwd=Path(cwd)))
        executor.execute(execution_req, hooks=hooks)
        

    def stop(self):
        for execution in self.execution_manager.get_running(kind=self.command_kind):
            execution.runner.terminate()
        
    @property 
    def is_running(self) -> bool:
        return bool(self.execution_manager.get_running(kind=self.command_kind))
        
        
    def on_closed(self, result: ExecutionResult, stderr: PytoyBuffer, cwd: Path) -> None: 
        error_msg = result.snapshot.stderr
        qflist = self._make_qflist(error_msg, cwd)
        handle_records(PytoyQuickfix(), records=qflist, is_open=False)
        if not error_msg:
            stderr.hide()

    def _make_qflist(self, string: str, cwd: Path) -> list[QuickfixRecord]:
        _pattern = re.compile(r'\s+File "(.+)", line (\d+)')
        result = list()
        lines = string.split("\n")
        index = 0
        while index < len(lines):
            infos = _pattern.findall(lines[index])
            if infos:
                filename, lnum = infos[0]
                row = dict()
                row["filename"] = filename
                row["lnum"] = lnum
                index += 1
                text = lines[index].strip()
                row["text"] = text
                record = QuickfixRecord.from_dict(row, cwd)
                result.append(record)
            index += 1
        result = list(reversed(result))
        return result
