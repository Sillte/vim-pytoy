from dataclasses import dataclass, field

from pytoy.job_execution.command_executor.executor import CommandExecutor
from pytoy.job_execution.command_executor.handler import CommandExecutionHandler
from pytoy.job_execution.command_executor.models import (
    BufferRequest,
    CommandExecutionEvents,
    CommandExecutionHooks,
    CommandExecutionQuery,
    CommandExecutionRequest,
    CommandExecutionResult,
)
from pytoy.job_execution.environment_manager import CommandExecutionWrapperType, CommandWrapperType, ExecutionPreference

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
