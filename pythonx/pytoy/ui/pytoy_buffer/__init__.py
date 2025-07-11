"""
This module is intended to provide the common interface for bufffer.

* vim
* neovim
* neovim+vscode

Usage: BufferExecutor / 

"""

from pytoy.ui.ui_enum import UIEnum, get_ui_enum
from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol



class PytoyBuffer(PytoyBufferProtocol):
    def __init__(self, impl: PytoyBufferProtocol):
        self._impl = impl

    @property
    def impl(self) -> PytoyBufferProtocol:
        """Return the implementation of PytoyBuffer."""
        return self._impl

    def init_buffer(self, content: str = ""):
        self._impl.init_buffer(content)

    def append(self, content: str) -> None:
        self._impl.append(content)

    @property
    def content(self) -> str:
        return self._impl.content

    def focus(self):
        return self._impl.focus()

    def hide(self):
        return self._impl.hide()


def make_buffer(stdout_name: str, mode: str = "vertical") -> PytoyBuffer:
    def make_vscode():
        from pytoy.ui.vscode.document import Document, Uri
        from pytoy.ui.pytoy_buffer.impl_vscode import PytoyBufferVSCode
        from pytoy.ui.vscode.document_user import make_document
        from pytoy.ui.vscode.focus_controller import store_focus, get_uri_to_views


        # sweep_editors()
        # [NOTE]: As of 2025/06/16, the method of initialization is different
        # in `make_buffer` and `make_duo_buffers`.
        uri = Uri(path=stdout_name, scheme="untitled")
        if uri in get_uri_to_views():
            document = Document(uri=uri)
        else:
            with store_focus():
                document = make_document(stdout_name)
        stdout_impl = PytoyBufferVSCode(document)
        return PytoyBuffer(stdout_impl)

    def make_vim():
        from pytoy.ui.vim import create_window
        from pytoy.ui.pytoy_buffer.impl_vim import PytoyBufferVim

        stdout_window = create_window(stdout_name, mode)
        stdout_impl = PytoyBufferVim(stdout_window.buffer)
        return PytoyBuffer(stdout_impl)

    ui_enum = get_ui_enum()
    creator = {UIEnum.VSCODE: make_vscode, UIEnum.VIM: make_vim, UIEnum.NVIM: make_vim}
    return creator[ui_enum]()


def make_duo_buffers(
    stdout_name: str, stderr_name: str
) -> tuple[PytoyBuffer, PytoyBuffer]:
    """Create 2 buffers, which is intended to `STDOUT` and `STDERR`."""

    def make_vscode():
        from pytoy.ui.vscode.document_user import (
            make_duo_documents,
            sweep_editors,
        )
        from pytoy.ui.vscode.focus_controller import store_focus
        from pytoy.ui.pytoy_buffer.impl_vscode import PytoyBufferVSCode

        sweep_editors()
        with store_focus():
            doc1, doc2 = make_duo_documents(stdout_name, stderr_name)
        stdout_impl = PytoyBufferVSCode(doc1)
        stderr_impl = PytoyBufferVSCode(doc2)
        return (PytoyBuffer(stdout_impl), PytoyBuffer(stderr_impl))

    def make_vim():
        from pytoy.ui.pytoy_window import PytoyWindowProvider

        stdout_window = PytoyWindowProvider().create_window(stdout_name, "vertical")
        stderr_window = PytoyWindowProvider().create_window(stderr_name, "horizontal", stdout_window)
        return (stdout_window.buffer, stderr_window.buffer)

    ui_enum = get_ui_enum()
    creator = {UIEnum.VSCODE: make_vscode, UIEnum.VIM: make_vim, UIEnum.NVIM: make_vim}
    return creator[ui_enum]()


if __name__ == "__main__":
    pass
