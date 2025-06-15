"""
This module is intended to provide the common interface for bufffer.

* vim
* neovim
* neovim+vscode

Usage: executors / 

"""

import vim
from typing import Protocol, Any, Type
from pytoy.ui_pytoy.ui_enum import UIEnum, get_ui_enum
from pytoy.ui_pytoy.vscode.document import Document


class PytoyBufferProtocol(Protocol):
    @classmethod
    def fetch_or_create(cls, specifier: str, **kwargs) -> "PytoyBufferProtocol":
        ...
        """Assure that the specifier `Buffer` exist in the UI.
        """

    def init_buffer(self, content: str = "") -> None:
        """Set the content of buffer"""

    def append(self, content: str) -> None:
        ...

    @property
    def content(self) -> str:
        ...

    @property
    def identifier(self) -> Any:
        ...

    def focus(self):
        ...

    def hide(self):
        ...


class PytoyBufferVim(PytoyBufferProtocol):
    def __init__(self, buffer: "vim.Buffer"):
        self.buffer = buffer

    @classmethod
    def fetch_or_create(
        cls,
        specifier: str,
        direction: str = "vertical",
        basewindow: Type["vim.Window"] | None = None,
        **kwargs
    ) -> "PytoyBufferVim":
        """Assure that the specifier `Buffer` exist in the UI."""
        from pytoy.ui_utils import create_window

        direction = kwargs.get("direction", "vertical")
        basewindow = kwargs.get("basewindow")

        window = create_window(specifier, direction, basewindow)
        return PytoyBufferVim(window.buffer)

    @property
    def identifier(self) -> int:
        """ """
        return self.buffer.number

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

    @classmethod
    def fetch_or_create(
        cls,
        specifier: str,
        direction: str = "vertical",
        basewindow: Type["vim.Window"] | None = None,
        **kwargs
    ) -> "PytoyBufferVSCode":
        """Assure that the specifier `Buffer` exist in the UI."""
        
        document = Document.create(specifier)
        return PytoyBufferVSCode(document)

    @property
    def identifier(self) -> str:
        """ """
        return self.document.uri.path

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
        pass


class PytoyBuffer:
    def __init__(
        self, impl: PytoyBufferProtocol | None = None, *, specifier: None | str = None
    ):
        if impl is None:
            assert specifier is not None
            ui_enum = get_ui_enum()
            if ui_enum == UIEnum.VSCODE:
                impl = PytoyBufferVSCode.fetch_or_create(specifier)
            else:
                impl = PytoyBufferVim.fetch_or_create(specifier)
        self._impl: PytoyBufferProtocol = impl

    def init_buffer(self, content: str = ""):
        self._impl.init_buffer(content)

    def append(self, content: str) -> None:
        self._impl.append(content)

    @property
    def identifier(self) -> Any:
        """ """
        return self._impl.identifier

    @property
    def content(self) -> str:
        return self._impl.content

    def focus(self):
        return self._impl.focus()

    def hide(self):
        return self._impl.hide()


def make_buffer(stdout_name: str, mode: str = "vertical") -> PytoyBuffer:
    ui_enum = get_ui_enum()
    
    if ui_enum == UIEnum.VSCODE:
        from pytoy.ui_pytoy.vscode.document_user import make_document, sweep_editors
        from pytoy.ui_pytoy.vscode.focus_controller import store_focus
        sweep_editors()
        with store_focus():
            uri = make_document(stdout_name)
        document = Document(uri=uri) 
        stdout_impl = PytoyBufferVSCode(document)
    else:
        from pytoy.ui_utils import create_window
        stdout_window = create_window(stdout_name, mode)
        stdout_impl = PytoyBufferVim(stdout_window.buffer)
    return PytoyBuffer(stdout_impl)

def make_duo_buffers(
    stdout_name: str, stderr_name: str
) -> tuple[PytoyBuffer, PytoyBuffer]:
    """Create 2 buffers, which is intended to `STDOUT` and `STDERR`. """
    ui_enum = get_ui_enum()

    if ui_enum == UIEnum.VSCODE:
        from pytoy.ui_pytoy.vscode.document_user import make_duo_documents, sweep_editors
        from pytoy.ui_pytoy.vscode.focus_controller import store_focus
        sweep_editors()
        with store_focus():
            uri1, uri2 = make_duo_documents(stdout_name, stderr_name)
        doc1 = Document(uri=uri1)
        doc2 = Document(uri=uri2)
        stdout_impl = PytoyBufferVSCode(doc1)
        stderr_impl = PytoyBufferVSCode(doc2)
    else:
        from pytoy.ui_utils import create_window
        stdout_window = create_window(stdout_name, "vertical")
        stderr_window = create_window(stderr_name, "horizontal", stdout_window)
        stdout_impl = PytoyBufferVim(stdout_window.buffer)
        stderr_impl = PytoyBufferVim(stderr_window.buffer)

    return (PytoyBuffer(stdout_impl), PytoyBuffer(stderr_impl))


if __name__ == "__main__":
    pass
