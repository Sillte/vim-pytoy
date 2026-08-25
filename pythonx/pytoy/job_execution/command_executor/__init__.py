from dataclasses import dataclass, field
from pytoy.job_execution.command_executor.executor import CommandExecutor
from pytoy.job_execution.environment_manager import ExecutionPreference, CommandWrapperType, CommandExecutionWrapperType

from pytoy.job_execution.command_executor.models import CommandExecutionEvents
from pytoy.job_execution.command_executor.models import CommandExecutionRequest
from pytoy.job_execution.command_executor.models import CommandExecutionHooks
from pytoy.job_execution.command_executor.models import BufferRequest


__all__ = [
    "CommandExecutor",
    "ExecutionHooks",
    "ExecutionEvents",
    "ExecutionRequest",
    "BufferRequest",
    "CommandExecutor",
]

__all__ += []


if __name__ == "__main__":
    executor = CommandExecutor("Pytoy:stdout")

    req = CommandExecutionRequest(command=["python", "-c", "print('hello world')"])

    executor.execute(req, hooks=CommandExecutionHooks())
