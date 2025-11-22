"""Exectuor for `Python`."""

import vim
import json
import re
from shlex import quote
from pathlib import  Path
from typing import Callable, Mapping
from dataclasses import dataclass

from pytoy.lib_tools.buffer_executor import BufferJobManager, BufferJobCreationParam, BufferJobProtocol

# `set_default_execution_mode` is carried out only in `__init__.py`
from pytoy.lib_tools.environment_manager import EnvironmentManager
from pytoy.lib_tools.utils import get_current_directory


from pytoy.ui import PytoyBuffer, PytoyQuickFix, handle_records

@dataclass
class PrevRunningState:
    cwd: Path  | str |  None = None
    path: Path | str | None = None
    env: Mapping[str, str] | None = None
    force_uv: bool | None = None

_PREV_STATE = PrevRunningState()

class PythonExecutor():
    job_name = "PythonExecutor"
    def __init__(self) -> None:
        pass

    def runfile(
        self,
        path: str | Path,
        stdout: PytoyBuffer,
        stderr: PytoyBuffer,
        *,
        cwd=None,
        env=None,
        force_uv=None,
    ):

        if cwd is None:
            cwd = get_current_directory()
        command = f'python -u -X utf8 "{path}"'
        
        _PREV_STATE.cwd = cwd
        _PREV_STATE.path = path
        _PREV_STATE.env = env
        _PREV_STATE.force_uv = force_uv
        self._run(command, stdout, stderr, cwd=cwd, env=env, force_uv=force_uv) 

    def rerun(self, stdout, stderr, force_uv=None):
        """Execute the previous `path`."""
        if _PREV_STATE.path is None:
            raise RuntimeError("Previous file is not existent.")

        cwd = _PREV_STATE.cwd
        path = _PREV_STATE.path
        env = _PREV_STATE.env
        force_uv = _PREV_STATE.force_uv

        return self.runfile(path, stdout, stderr, cwd=cwd, force_uv=force_uv, env=env)

    def stop(self):
        BufferJobManager.stop(self.job_name)
        
    @property 
    def is_running(self) -> bool:
        return BufferJobManager.is_running(self.job_name)
        

    def _run(self,
            command: str,
            stdout: PytoyBuffer,
            stderr: PytoyBuffer,
            cwd: str | Path | None = None,
            env: dict[str, str] | None = None,
            *,
            force_uv: bool | None = None):
        wrapper = EnvironmentManager().get_command_wrapper(force_uv=force_uv)
        wrapped_command  = wrapper(command)
        param = BufferJobCreationParam(command=wrapped_command,
                                       cwd=cwd,
                                       env=env,
                                       stdout=stdout,
                                       stderr=stderr,
                                       on_closed=self.on_closed)

        if BufferJobManager.is_running(self.job_name):
            raise ValueError(f"`{self.job_name=}` is already running")
        BufferJobManager.create(self.job_name, param)
        

    def on_closed(self, buffer_job: BufferJobProtocol) -> None:
        assert buffer_job.stderr is not None
        error_msg = buffer_job.stderr.content.strip()

        qflist = self._make_qflist(error_msg)
        handle_records(PytoyQuickFix(cwd=buffer_job.cwd), records=qflist, win_id=None, is_open=False)
        if not error_msg:
            buffer_job.stderr.hide()

    def _make_qflist(self, string):
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
                result.append(row)
            index += 1
        result = list(reversed(result))
        return result
