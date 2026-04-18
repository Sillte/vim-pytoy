" ""Exectuor for `Python`."""
import re

from pathlib import  Path

from pytoy.job_execution.command_executor.launcher import LaunchProfile
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
        hooks = make_quickfix_hooks(quickfix_profile)

        command_profile = LaunchProfile(kind="PythonExecutor",
                                         command_wrapper=command_wrapper,
                                         execution_hooks=hooks)

        self.script_runner = CommandLauncher(launch_profile=command_profile)
        
    @property
    def buffers(self) -> tuple[PytoyBuffer, PytoyBuffer]:
        ...
    
        
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
        force_uv: bool = False,
    ):
        command = self._make_command(path)
        self.script_runner.run(command, stdout, stderr, cwd=cwd, init_buffer=True)
    
    def rerun(self, stdout: PytoyBuffer, stderr: PytoyBuffer):
        self.script_runner.rerun(stdout, stderr)

    def stop(self):
        self.script_runner.stop()
        
    @property
    def is_running(self) -> bool:
        return self.script_runner.is_running





