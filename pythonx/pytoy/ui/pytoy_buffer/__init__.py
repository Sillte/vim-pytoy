"""
This module is intended to provide the common interface for bufffer.

* vim
* neovim
* neovim+vscode

Usage: BufferExecutor / 

"""
from pathlib import Path
from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol, RangeSelectorProtocol
from pytoy.ui.pytoy_buffer.queue_updater import QueueUpdater  # noqa
from pytoy.ui.pytoy_buffer.range_selector import make_selector  #noqa


class PytoyBuffer(PytoyBufferProtocol):
    def __init__(self, impl: PytoyBufferProtocol):
        self._impl = impl

    @classmethod
    def get_current(cls):
        return PytoyBuffer(_get_current_impl())

    @property
    def impl(self) -> PytoyBufferProtocol:
        """Return the implementation of PytoyBuffer."""
        return self._impl

    @property
    def path(self) -> Path:
        """Return the implementation of PytoyBuffer."""
        return self.impl.path
    

    @property
    def is_file(self) -> bool:
        """Return whether this buffer corresponds to the file or not."""
        return self.impl.is_file

    @property
    def valid(self) -> bool:
        return self.impl.valid

    def init_buffer(self, content: str = ""):
        self._impl.init_buffer(content)

    def append(self, content: str) -> None:
        self._impl.append(content)

    @property
    def content(self) -> str:
        return self._impl.content

    def show(self):
        return self._impl.show()

    def hide(self):
        return self._impl.hide()

    def get_lines(self, line1: int, line2: int) -> list[str]:
        range_selector: RangeSelectorProtocol = make_selector(self.impl)
        return range_selector.get_lines(line1, line2)

    def get_range(self, line1: int, pos1: int, line2: int, pos2: int) -> str:
        range_selector: RangeSelectorProtocol = make_selector(self.impl)
        return range_selector.get_range(line1, pos1, line2, pos2)


def make_buffer(stdout_name: str, mode: str = "vertical") -> PytoyBuffer:
    from pytoy.ui.pytoy_window import PytoyWindowProvider
    stdout_window = PytoyWindowProvider().create_window(stdout_name, mode)
    return stdout_window.buffer


def make_duo_buffers(
    stdout_name: str, stderr_name: str
) -> tuple[PytoyBuffer, PytoyBuffer]:
    """Create 2 buffers, which is intended to `STDOUT` and `STDERR`."""

    from pytoy.ui.pytoy_window import PytoyWindowProvider
    stdout_window = PytoyWindowProvider().create_window(stdout_name, "vertical")
    stderr_window = PytoyWindowProvider().create_window(stderr_name, "horizontal", stdout_window)
    return (stdout_window.buffer, stderr_window.buffer)


def _get_current_impl() -> PytoyBufferProtocol:
    from pytoy.ui.ui_enum import get_ui_enum, UIEnum
    ui_enum = get_ui_enum()
    if ui_enum == UIEnum.VSCODE:
        from pytoy.ui.pytoy_buffer.impl_vscode import PytoyBufferVSCode
        current_impl = PytoyBufferVSCode.get_current()
    else:
        from pytoy.ui.pytoy_buffer.impl_vim import PytoyBufferVim
        current_impl = PytoyBufferVim.get_current()
    return current_impl


if __name__ == "__main__":
    pass
