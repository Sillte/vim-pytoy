import threading

from pytoy.tool_execution.terminal import (
    BufferRequest,
    ShellDriver,
    TerminalExecutionHandler,
    TerminalExecutionHooks,
    TerminalExecutionRequest,
)


def test_handler_starts_terminal_and_notifies_on_exit() -> None:
    finished = threading.Event()
    results = []
    exits = []

    def on_result(result):
        results.append(result)
        finished.set()

    def on_exit(_):
        exits.append(True)

    handler = TerminalExecutionHandler.create(
        TerminalExecutionRequest(driver=ShellDriver()),
        BufferRequest.from_no_file("terminal-handler-test"),
    )
    handler.on_exit.subscribe(on_exit)

    handler.start(TerminalExecutionHooks(on_result=on_result))
    handler.send("exit")

    assert finished.wait(5)
    assert len(exits) == 1
    assert len(results) == 1
    assert results[0].exit_code == 0
