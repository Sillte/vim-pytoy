from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.job_execution.terminal_executor.models import DriverKind, TerminalDriverProtocol
from pytoy.job_execution.terminal_runner.drivers import TerminalDriverManager
from pytoy.shared.lib.text import LineRange
from pytoy.shared.ui.pytoy_window import PytoyWindow
from pytoy.tools.markdown import MarkdownExtractor


from pathlib import Path
from typing import Literal


class TerminalSelector:
    def __init__(self, driver_manager: TerminalDriverManager | None = None):
        ctx = GlobalPytoyContext.get()
        self._driver_manager = driver_manager or ctx.terminal_driver_manager

    def _to_driver_kind(self, driver: DriverKind | TerminalDriverProtocol) -> DriverKind:
        return  driver if isinstance(driver, str) else driver.kind

    @property
    def driver_manager(self) -> TerminalDriverManager:
        return self._driver_manager

    @property
    def default_buffer(self) -> str:
        return "__TERMINAL__"

    def get_preferrable_driver(self, input: str | Path | PytoyWindow | TerminalDriverProtocol | None = None, line_range: LineRange | None = None, cwd: Path | None = None) -> Literal["ipython", "shell"] | TerminalDriverProtocol:
        if isinstance(input, TerminalDriverProtocol):
            return input

        if isinstance(input, str):
            match input:
                case "ipython":
                    return "ipython"
                case "shell":
                    return "shell"

        if isinstance(input, (Path, str)):
            path = Path(input)
            if path.suffix == ".py":
                if self.driver_manager._is_registered("ipython"):
                    return "ipython"
            return "shell"
        elif isinstance(input, PytoyWindow):
            window = input
            buffer = window.buffer
            text = buffer.content
            structure = MarkdownExtractor(text).structure
            cursor = window.cursor
            block = structure.get_current_code_block(cursor.line)
            if not block:
                raise ValueError("For `markdown`, the outside of `code block` is not determined.")
            if block.type == "python":
                return "ipython"
            else:
                return "shell"
        else:
            return "shell"


    def get_preferrable_buffer(self, input: str | Path | PytoyWindow | TerminalDriverProtocol | None, line_range: LineRange | None = None, cwd: Path | None = None) -> str:
        if input is None:
            return self.default_buffer
        driver = self.get_preferrable_driver(input, line_range=line_range, cwd=cwd)
        driver_kind = self._to_driver_kind(driver)
        match driver_kind:
            case "ipython":
                return "__IPYTYON__"
            case "shell":
                return "__SHELL__"
            case _:
                return self.default_buffer