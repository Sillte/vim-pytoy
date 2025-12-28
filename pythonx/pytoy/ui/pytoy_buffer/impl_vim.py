import vim
from pathlib import Path
from pytoy.ui.pytoy_buffer.models import Selection


VIM_ERROR = getattr(vim, "error", Exception)

from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol, RangeSelectorProtocol


class PytoyBufferVim(PytoyBufferProtocol):
    def __init__(self, buffer: "vim.Buffer"):
        self.buffer = buffer

    def init_buffer(self, content: str = "") -> None:
        """Set the content of buffer"""
        content = content.replace("\r\n", "\n")
        self.buffer[:] = content.split("\n")

    @classmethod
    def get_current(cls) -> PytoyBufferProtocol:
        return PytoyBufferVim(vim.current.buffer)

    @property
    def path(self) -> Path:
        return Path(self.buffer.name)

    @property
    def is_file(self) -> bool:
        buftype = vim.eval(f"getbufvar({self.buffer.number}, '&buftype')")
        return buftype == "" and bool(self.buffer.name)

    @property
    def is_normal_type(self) -> bool:
        """Return whether the buffer is regarded as editable by pytoy.

        Treat buffers with non-empty 'buftype' or non-modifiable buffers as
        non-normal.
        """
        try:
            buftype = vim.eval(f"getbufvar({self.buffer.number}, '&buftype')")
            return buftype in {"", "nofile"}
        except VIM_ERROR:
            return False
        except (AttributeError, TypeError):
            return False

    @property
    def valid(self) -> bool:
        return self.buffer.valid

    def append(self, content: str) -> None:
        if not content:
            return
        content = content.replace("\r\n", "\n")
        lines = content.split("\n")
        if self._is_empty():
            self.buffer[:] = [lines[0]]
        else:
            self.buffer.append(lines[0])
        for line in lines[1:]:
            self.buffer.append(line)

    @property
    def content(self) -> str:
        return vim.eval("join(getbufline({}, 1, '$'), '\n')".format(self.buffer.number))

    def show(self):
        bufnr = self.buffer.number
        winid = int(vim.eval(f"bufwinid({bufnr})"))
        if winid != -1:
            vim.command(f"call win_gotoid({winid})")
        else:
            vim.command(f"buffer {bufnr}")

    def hide(self):
        nr = int(vim.eval(f"bufwinnr({self.buffer.number})"))
        if 0 <= nr:
            vim.command(f":{nr}close")

    def _is_empty(self) -> bool:
        if len(self.buffer) == 0:
            return True
        if len(self.buffer) == 1 and self.buffer[0] == "":
            return True
        return False


class RangeSelectorVim(RangeSelectorProtocol):
    def __init__(self, buffer: PytoyBufferVim):
        self._buffer = buffer

    @property
    def buffer(self) -> PytoyBufferVim:
        return self._buffer

    def get_lines(self, line1: int, line2: int) -> list[str]:
        """Note that line1 and line2 is 0-based.
        """
        bufnr = self._buffer.buffer.number
        return vim.eval(f"getbufline({bufnr}, {line1 + 1}, {line2 + 1})")

    def get_range(self, selection: Selection) -> str:
        """`line` and `pos` are number acquried by `getpos`."""
        # Note that `start.line` and `end.line` is 0-based.
        # Note that `start.col` and `end.col` is 0-based.
        start, end  = selection.start, selection.end
        line1, line2 = start.line, end.line
        col1, col2 = start.col, end.col
        lines: list[str] = self.get_lines(line1, line2)
        if not lines:
            return ""

        if line1 == line2:
            return lines[0][col1 : col2 + 1]

        lines[0] = lines[0][col1 :]
        lines[-1] = lines[-1][: col2 + 1]
        return "\n".join(lines)

    def replace_range(self, selection: Selection, text: str) -> None:
        start, end = selection.start, selection.end
        lines = self.get_lines(start.line, end.line)
        if not lines:
            return

        head = lines[0][:start.col]
        tail = lines[-1][end.col + 1:] # Because it is inclusive.

        new_content_lines = text.split("\n")
        new_content_lines[0] = head + new_content_lines[0]
        new_content_lines[-1] = new_content_lines[-1] + tail

        self.buffer.buffer[start.line : end.line + 1] = new_content_lines
