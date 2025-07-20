"""
This module is intended to provide the common interface for bufffer.

* vim
* neovim
* neovim+vscode

Usage: BufferExecutor / 

"""

from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol
from pytoy.ui.pytoy_buffer.queue_updater import QueueUpdater  # noqa


class PytoyBuffer(PytoyBufferProtocol):
    def __init__(self, impl: PytoyBufferProtocol):
        self._impl = impl

    @property
    def impl(self) -> PytoyBufferProtocol:
        """Return the implementation of PytoyBuffer."""
        return self._impl

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


if __name__ == "__main__":
    pass
