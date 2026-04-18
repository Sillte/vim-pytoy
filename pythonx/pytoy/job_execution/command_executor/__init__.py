from dataclasses import dataclass, field
from pytoy.job_execution.command_executor.executor import CommandExecutor
from pytoy.job_execution.environment_manager import ExecutionPreference, CommandWrapperType, ExecutionWrapperType  

from pytoy.job_execution.command_executor.models import ExecutionEvents
from pytoy.job_execution.command_executor.models import ExecutionRequest
from pytoy.job_execution.command_executor.models import ExecutionHooks
from pytoy.job_execution.command_executor.models import BufferRequest


__all__ = ["CommandExecutor",
           "ExecutionHooks", 
           "ExecutionEvents",
           "ExecutionRequest",
           "BufferRequest", 
           "CommandExecutor"]

__all__ += []




if __name__ == "__main__":
    executor = CommandExecutor("Pytoy:stdout")

    req = ExecutionRequest(
        command=["python", "-c", "print('hello world')"]
    )

    executor.execute(req, hooks=ExecutionHooks())
    

