from pathlib import Path

from pytoy.shared.lib.text import LineRange
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer
from pytoy.shared.ui.pytoy_window import PytoyWindow
from pytoy.tool_execution.terminal_executor.controller import TerminalExecutionController
from pytoy.tools.console.selector import TerminalSelector


class ConsoleRunner:
    def __init__(self):
        self._controller = TerminalExecutionController()
        self._selector = TerminalSelector()

    @property
    def controller(self) -> TerminalExecutionController:
        return self._controller

    @property
    def selector(self) -> TerminalSelector:
        return self._selector

    def run(self, cmd: str, buffer: str | None, driver: str | None = None, cwd: Path | str | None = None):
        current_window = PytoyWindow.get_current()
        cwd = Path(cwd) if cwd else current_window.buffer.file_path.parent
        resolved_driver = driver or self.selector.get_preferrable_driver(current_window)
        resolved_buffer = buffer or self.selector.get_preferrable_buffer(current_window)
        handler = self.controller.get_or_create_handler(
            resolved_driver,
            resolved_buffer,
            cwd=cwd,
        )
        handler.send(cmd)

    def stop(self, buffer: str | None, driver: str | None = None, cwd: Path | str | None = None):
        input = driver or PytoyWindow.get_current()
        resolved_buffer = buffer or self.selector.get_preferrable_buffer(input)
        self.controller.stop(resolved_buffer)

    def terminate(self, buffer: str, driver: str | None = None):
        self.controller.terminate(buffer)

    def send(self, buffer: str | None, driver: str | None, line_range: LineRange, cwd: str | Path | None = None):
        cwd = Path(cwd) if cwd else PytoyBuffer.get_current().file_path.parent
        from pytoy.shared.ui.pytoy_window import PytoyWindow

        input = driver or PytoyWindow.get_current()
        resolved_driver = driver or self.selector.get_preferrable_driver(input)
        resolved_buffer = buffer or self.selector.get_preferrable_buffer(resolved_driver)
        lines = PytoyBuffer.get_current().get_lines(line_range)
        content = "\n".join(lines)
        self.controller.send(resolved_driver, resolved_buffer, content=content, cwd=cwd)
