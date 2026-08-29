from dataclasses import dataclass, field

from pytoy.job_execution.environment_manager import CommandExecutionWrapperType
from pytoy.tool_execution.command_executor.executor import CommandExecutor
from pytoy.tool_execution.command_executor.handler import CommandExecutionHandler
from pytoy.tool_execution.command_executor.models import (
    BufferRequest,
    CommandExecutionEvents,
    CommandExecutionHooks,
    CommandExecutionID,
    CommandExecutionKind,
    CommandExecutionQuery,
    CommandExecutionRequest,
    CommandExecutionResult,
    CommandExecutionStatus,
)

__all__ = [
    "CommandExecutor",
    "CommandExecutionHandler",
    "CommandExecutionRequest",
    "CommandExecutionHooks",
    "CommandExecutionEvents",
    "CommandExecutionResult",
    "CommandExecutionQuery",
    "BufferRequest",
    "CommandExecutionWrapperType",
    "CommandExecutionID",
    "CommandExecutionStatus",
    "CommandExecutionKind",
]


if __name__ == "__main__":
    executor = CommandExecutor("Pytoy:stdout")

    req = CommandExecutionRequest(command=["python", "-c", "print('hello world')"])

    executor.execute(req, hooks=CommandExecutionHooks())
