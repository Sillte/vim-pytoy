"""
This module is intended to provide the common interface for bufffer.

* vim
* neovim
* neovim+vscode

Usage: executors / 

"""

import vim
from typing import Protocol
from pytoy.ui.ui_enum import UIEnum, get_ui_enum
from pytoy.ui.vscode.document import Document, Uri


class PytoyBufferProtocol(Protocol):
    def init_buffer(self, content: str = "") -> None:
        """Set the content of buffer"""

    def append(self, content: str) -> None:
        ...

    @property
    def content(self) -> str:
        ...

    def focus(self):
        ...

    def hide(self):
        ...


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

    def focus(self):
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


class PytoyBufferVSCode(PytoyBufferProtocol):
    def __init__(self, document: Document):
        self.document = document

    def init_buffer(self, content: str = "") -> None:
        """Set the content of buffer"""
        if content and content[-1] != "\n":
            content += "\n"
        self.document.content = content

    def append(self, content: str) -> None:
        if not content:
            return
        self.document.append(content)

    @property
    def content(self) -> str:
        return self.document.content

    def focus(self):
        self.document.show()

    def hide(self):
        # [NOTE]: Due to the difference of management of window and `Editor` in vscode
        # this it not implemented.
        pass


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

        sweep_editors()
        with store_focus():
            doc1, doc2 = make_duo_documents(stdout_name, stderr_name)
        stdout_impl = PytoyBufferVSCode(doc1)
        stderr_impl = PytoyBufferVSCode(doc2)
        return (PytoyBuffer(stdout_impl), PytoyBuffer(stderr_impl))

    def make_vim():
        from pytoy.ui.vim import create_window

        stdout_window = create_window(stdout_name, "vertical")
        stderr_window = create_window(stderr_name, "horizontal", stdout_window)
        stdout_impl = PytoyBufferVim(stdout_window.buffer)
        stderr_impl = PytoyBufferVim(stderr_window.buffer)
        return (PytoyBuffer(stdout_impl), PytoyBuffer(stderr_impl))

    ui_enum = get_ui_enum()
    creator = {UIEnum.VSCODE: make_vscode, UIEnum.VIM: make_vim, UIEnum.NVIM: make_vim}
    return creator[ui_enum]()


if __name__ == "__main__":
    pass
