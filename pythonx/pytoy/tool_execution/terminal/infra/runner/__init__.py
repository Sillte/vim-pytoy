"""Terminal job runner."""

from __future__ import annotations

from pytoy.tool_execution.terminal.drivers.shell import ShellDriver

from .runner import TerminalJobRunner

__all__ = [
    "TerminalJobRunner",
]

if __name__ == "__main__":
    # Simple Tests.
    from pytoy.shared.timertask import TimerTask
    from pytoy.shared.ui.pytoy_window import PytoyWindowProvider
    from pytoy.tool_execution.terminal.drivers.ipython import IPythonDriver
    from pytoy.tool_execution.terminal.infra.runner.models import TerminalJobRequest
    # driver = ShellDriver("cmd.exe")

    driver = IPythonDriver()
    window = PytoyWindowProvider().open_window("MOCK", "vertical")

    request = TerminalJobRequest(driver=driver)
    job_runner = TerminalJobRunner(
        request,
        window.buffer,
    )
    job_runner.run()

    TimerTask.execute_oneshot(lambda: job_runner.send("dir"), interval=500)
    TimerTask.execute_oneshot(lambda: job_runner.send("echo BAfAFAF"), interval=1200)
    TimerTask.execute_oneshot(lambda: print(job_runner.snapshot.content), interval=3000)  # type: ignore
