" ""Exectuor for `Python`."""
import re

from pathlib import  Path

from pytoy.job_execution.command_executor.launcher import LaunchProfile, get_default_hooks, ExecutionHooks
from pytoy.job_execution.command_executor.launcher.quickfix import QuickfixProfile, make_quickfix_hooks

from pytoy.shared.ui import PytoyBuffer, QuickfixRecord

from pytoy.job_execution.command_executor.launcher import CommandLauncher
from typing import Sequence



class PythonExecutor:
    def __init__(self, *, force_uv: bool = False):

        command_wrapper="uv" if force_uv else "auto"

        def quickfix_creator(text: str, cwd: Path) -> Sequence[QuickfixRecord]:
            _pattern = re.compile(r'\s+File "(.+)", line (\d+)')
            result = list()
            lines = text.split("\n")
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
        quickfix_profile = QuickfixProfile(quickfix_creator=quickfix_creator)
        quickfix_hooks = make_quickfix_hooks(quickfix_profile)
        default_hooks = get_default_hooks()
        hooks = ExecutionHooks.merge(quickfix_hooks, default_hooks)
        command_profile = LaunchProfile(kind="PythonExecutor",
                                         command_wrapper=command_wrapper,
                                         execution_hooks=hooks)

        self.command_launcher = CommandLauncher(launch_profile=command_profile)
        
        
    def _make_command(self, path: str | Path) -> str:
        command = " ".join(["python", "-u", "-X", "utf8", Path(path).as_posix()])
        return command

        
    def runfile(
        self,
        path: str | Path,
        stdout: PytoyBuffer,
        stderr: PytoyBuffer,
        *,
        cwd: Path | None=None,
    ):
        command = self._make_command(path)
        self.command_launcher.run(command, stdout, stderr, cwd=cwd, init_buffer=True)
    
    def rerun(self, stdout: PytoyBuffer, stderr: PytoyBuffer):
        self.command_launcher.rerun(stdout, stderr)

    def stop(self):
        self.command_launcher.stop()
        
    @property
    def is_running(self) -> bool:
        return self.command_launcher.is_running





