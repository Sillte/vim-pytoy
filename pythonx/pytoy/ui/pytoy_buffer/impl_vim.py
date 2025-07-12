import vim
from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol


class PytoyBufferVim(PytoyBufferProtocol):
    def __init__(self, buffer: "vim.Buffer"):
        self.buffer = buffer

    def init_buffer(self, content: str = "") -> None:
        """Set the content of buffer"""
        self.buffer[:] = content.split("\n")

    def append(self, content: str) -> None:
        if not content:
            return
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