from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

from pytoy.shared.ui.pytoy_buffer import make_duo_buffers
from pytoy.tool_execution.terminal.infra.contract.models import (
    TerminalJobRequest,
)

from .runner import TerminalJobRunner

if __name__ == "__main__":
    # Simple Tests.
    from pytoy.shared.timertask import TimerTask
    from pytoy.shared.ui.pytoy_window.facade import PytoyWindowProvider
    from pytoy.tool_execution.terminal.infra.driver import IPythonDriver, ShellDriver
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
