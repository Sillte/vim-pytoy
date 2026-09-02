import threading
from pathlib import Path

from pytoy.tool_execution.command import (
    BufferRequest,
    CommandExecutionHooks,
    CommandExecutionRequest,
    CommandExecutionResult,
    CommandExecutor,
)


def test_executor_exposes_resolved_buffers() -> None:
    executor = CommandExecutor(BufferRequest.from_str("executor-output"))

    assert executor.stdout.uri.path == "executor-output"
    assert executor.stderr is None


def test_executor_runs_command() -> None:
    finished = threading.Event()
    results = []
    executor = CommandExecutor("executor-output")
    request = CommandExecutionRequest(
        command=["python", "-c", "print('hello from executor')"],
        command_wrapper="system",
        cwd=Path.cwd(),
        kind="executor-test",
    )

    def on_result(result: CommandExecutionResult):
        results.append(result)
        finished.set()

    handler = executor.execute(
        request,
        CommandExecutionHooks(on_result=on_result),
    )
    assert handler.id
    assert finished.wait(5)
    assert len(results) == 1
    assert results[0].stdout == "hello from executor"
