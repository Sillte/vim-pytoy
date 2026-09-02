import threading
from pathlib import Path

import pytest

from pytoy.tool_execution.command import (
    BufferRequest,
    CommandExecutionHandler,
    CommandExecutionHooks,
    CommandExecutionQuery,
    CommandExecutionRequest,
)


def test_create_exposes_handler_for_new_execution() -> None:
    handler = CommandExecutionHandler.create(
        CommandExecutionRequest(
            command=["python", "-c", "print('hello')"], command_wrapper="system", cwd=Path.cwd(), kind="test"
        ),
        BufferRequest.from_str("command-output"),
    )

    assert handler.id
    assert handler.status == "created"
    assert handler.command == "python -c print('hello')"
    queried = CommandExecutionHandler.query(CommandExecutionQuery(kind="test"))
    assert [item.id for item in queried] == [handler.id]


def test_start_runs_command_and_records_last_context() -> None:
    finished = threading.Event()
    handler = CommandExecutionHandler.create(
        CommandExecutionRequest(
            command=["python", "-c", "print('hello')"], command_wrapper="system", cwd=Path.cwd(), kind="test"
        ),
        BufferRequest.from_str("command-output"),
    )
    stdout = handler.stdout

    handler.start(CommandExecutionHooks(on_result=lambda _: finished.set()))

    assert finished.wait(5)
    context = CommandExecutionHandler.get_last_context("test")
    assert context is not None
    assert stdout.content == "hello"


def test_start_failure_does_not_leave_handler_running() -> None:
    exceptions = []
    handler = CommandExecutionHandler.create(
        CommandExecutionRequest(
            command=["__pytoy_command_that_does_not_exist__"],
            command_wrapper="system",
            cwd=Path.cwd(),
            kind="failed-start",
        ),
        BufferRequest.from_str("failed-command-output"),
    )

    with pytest.raises(FileNotFoundError):
        handler.start(CommandExecutionHooks(on_exception=exceptions.append))

    assert len(exceptions) == 1
    assert isinstance(exceptions[0], FileNotFoundError)
    assert handler.status is None
