from dataclasses import dataclass, field
from pytoy.job_execution.command_executor.executor import CommandExecutor
from pytoy.job_execution.environment_manager import ExecutionPreference, CommandWrapperType, CommandExecutionWrapperType

from pytoy.job_execution.command_executor.models import CommandExecutionEvents
from pytoy.job_execution.command_executor.models import CommandExecutionRequest
from pytoy.job_execution.command_executor.models import CommandExecutionHooks
from pytoy.job_execution.command_executor.models import CommandExecutionResult
from pytoy.job_execution.command_executor.models import CommandExecutionQuery
from pytoy.job_execution.command_executor.models import BufferRequest
from pytoy.job_execution.command_executor.handler import CommandExecutionHandler


__all__ = [
    "CommandExecutor",
    "CommandExecutionHooks",
    "CommandExecutionEvents",
    "CommandExecutionRequest",
    "CommandExecutionHandler",
    "CommandExecutionResult",
    "CommandExecutionQuery",
    "BufferRequest",
]

__all__ += []


if __name__ == "__main__":
    executor = CommandExecutor("Pytoy:stdout")

    req = CommandExecutionRequest(command=["python", "-c", "print('hello world')"])

    executor.execute(req, hooks=CommandExecutionHooks())
