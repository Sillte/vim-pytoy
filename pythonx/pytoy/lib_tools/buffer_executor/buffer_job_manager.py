from pathlib import Path
from typing import Callable, Any

from pytoy.ui import PytoyBuffer

from pytoy.lib_tools.buffer_executor.buffer_job import (
    make_buffer_job,
    BufferJobProtocol,
)


from dataclasses import dataclass 
from typing import Mapping

        
@dataclass
class BufferJobCreationParam:
    command: str | list[str]
    stdout: PytoyBuffer
    stderr: PytoyBuffer | None = None
    cwd: Path | str | None = None
    env: Mapping[str, str] | None = None
    on_closed: Callable[[BufferJobProtocol], Any] | None = None
        

type BufferJobName = str
class BufferJobManager:

    buffer_jobs: dict[str, BufferJobProtocol] = dict()
    
    @staticmethod
    def create(name: str, creation_param: BufferJobCreationParam) -> BufferJobProtocol:
        if BufferJobManager.is_running(name):
                msg = f"`{name}` buffer job is already running."
                raise ValueError(msg)

        buffer_job = make_buffer_job(
            name=name,
            stdout=creation_param.stdout,
            stderr=creation_param.stderr,
        )

        stdout=creation_param.stdout
        stderr=creation_param.stderr
        command = creation_param.command
        env=creation_param.env
        cwd=creation_param.cwd
        if not isinstance(command, str):
            command = " ".join(command) 

        if stdout:
            stdout.init_buffer(command)
        if stderr:
            stderr.init_buffer()

        BufferJobManager.buffer_jobs[name] = buffer_job 
        
        def prepare() -> Mapping:
            return {}
        def dummy_on_closed(buffer_job: BufferJobProtocol) -> None:
            return None
        on_closed = creation_param.on_closed or dummy_on_closed
        buffer_job.job_start(command, prepare, on_closed, cwd=cwd, env=env)
        return buffer_job

    @staticmethod
    def get(name: str) -> BufferJobProtocol | None:
        return BufferJobManager.buffer_jobs.get(name)

    @staticmethod
    def is_running(name: str) -> bool:
        buffer_job = BufferJobManager.get(name)
        print("buffer_job_is_running", buffer_job)
        return bool(buffer_job and buffer_job.is_running)
    
    @staticmethod
    def stop(name: str) -> None:
        buffer_job = BufferJobManager.get(name)
        if buffer_job:
            buffer_job.stop() 

    

if __name__ == "__main__":
    pass
