import time
from queue import Empty
from .impl_main import TerminalBackendImplProvider
from .application import ShellApplication

shell = ShellApplication()


def test_start_and_send_echo(terminal=None):
    if terminal is None:
        terminal = TerminalBackendImplProvider().provide(app=shell)
    if not terminal.alive:
        terminal.start()

    assert terminal.alive, "Terminal should be alive after start"

    terminal.send("echo HelloTest")

    time.sleep(3)

    result_lines = []
    while True:
        try:
            lines = terminal.queue.get_nowait()
        except Empty:
            break
        result_lines += lines

    joined = "\n".join(result_lines)
    assert (
        "HelloTest" in joined
    ), f"Expected 'HelloTest' in output, got:\n{joined} \n{terminal._line_buffer.chunk}"
    terminal.terminate()


def test_send_multiple_lines():
    terminal = TerminalBackendImplProvider().provide(app=shell)
    terminal.start()
    terminal.send("echo Line1")
    terminal.send("echo Line2")
    terminal.send("echo Line3")
    time.sleep(0.5)

    result = []
    while True:
        try:
            lines = terminal.queue.get_nowait()
        except Empty:
            break
        result += lines

    terminal.terminate()

    output = "\n".join(result)
    assert (
        "Line1" in output and "Line2" in output and "Line3" in output
    ), "Expected all lines in output"


def test_interrupt_safe_call():
    terminal = TerminalBackendImplProvider().provide(app=shell)
    terminal.start()
    terminal.send("timeout /t 2 > NUL")  # Sleep equivalent
    time.sleep(0.5)
    try:
        terminal.interrupt()
    except Exception as e:
        assert False, f"Interrupt raised exception: {e}"

    test_start_and_send_echo(terminal)


def test_busy_behavior():
    terminal = TerminalBackendImplProvider().provide(app=shell)
    terminal.start()

    assert not terminal.busy, "Terminal should not be busy immediately after start"

    terminal.send("timeout /t 2 > NUL")  # Windows専用のsleep
    time.sleep(0.3)  # 少し待って busy 状態を観測

    assert terminal.busy, "Terminal should be busy after sending a blocking command"

    time.sleep(2.5)  # timeout 終了待ち
    assert not terminal.busy, "Terminal should not be busy after command completes"

    terminal.terminate()


def main():
    terminal = TerminalBackendImplProvider().provide(app=shell)
    terminal.send("echo hello")
    time.sleep(2)

    result_lines = []
    while True:
        try:
            lines = terminal.queue.get_nowait()
        except Empty:
            break
        result_lines += lines
    print("Check", "".join(result_lines))

    print("Running TerminalBackendWin tests...")

    test_start_and_send_echo()
    print("✅ echo test passed.")
    test_send_multiple_lines()
    print("✅ multiple echo lines passed.")

    test_interrupt_safe_call()
    print("✅ Interrupt test passed.")

    test_start_and_send_echo()
    print("✅ echo test passed.")

    print("✅ interrupt test passed.", flush=True)
    test_busy_behavior()
    print("✅ busy behavior.")


if __name__ == "__main__":
    main()
