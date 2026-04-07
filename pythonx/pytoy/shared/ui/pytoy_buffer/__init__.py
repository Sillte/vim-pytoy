"""
This module is intended to provide the common interface for bufffer.

* vim
* neovim
* neovim+vscode

"""

from pathlib import Path
from typing import Literal, TYPE_CHECKING, Sequence, Self
from pytoy.shared.ui.pytoy_buffer.models import BufferEvents, URI, BufferSource, BufferQuery
from pytoy.shared.ui.pytoy_buffer.protocol import PytoyBufferProtocol, RangeOperatorProtocol, PytoyBufferProviderProtocol, Event, BufferID
from pytoy.shared.lib.text import CharacterRange, LineRange

if TYPE_CHECKING:
    from pytoy.shared.ui.pytoy_window import PytoyWindow


class PytoyBuffer(PytoyBufferProtocol):
    def __init__(self, impl: PytoyBufferProtocol):
        self._impl = impl

    @property
    def buffer_id(self) -> BufferID:
        return self._impl.buffer_id

    @property
    def on_wiped(self) -> Event[BufferID]:
        return self._impl.on_wiped

    @property
    def events(self) -> BufferEvents:
        return self._impl.events

    @classmethod
    def get_current(cls) -> "PytoyBuffer":
        return PytoyBufferProvider().get_current()

    @property
    def impl(self) -> PytoyBufferProtocol:
        """Return the implementation of PytoyBuffer."""
        return self._impl

    @property
    def path(self) -> Path | None:
        """Return the path of buffer.
        If `is_file` is True, it corresponds to the file path.
        If not, this is related to the buffername (vim/nvim) or `uri.path` (vscode).
        """
        source = self.source
        if source.type == "file":
            return Path(source.name)
        else:
            return None
    
    @property
    def source(self) -> BufferSource:
        """Return the source of buffer."""
        return self.impl.source
    
    @property
    def uri(self) -> URI:
        return self.impl.uri

    @property
    def is_file(self) -> bool:
        """Return whether this buffer corresponds to the file or not."""
        return self.impl.is_file
    
    @property
    def file_path(self) -> Path:
        """Return the path of buffer.
        It is assured that the return path is the path to the physical location.
        """
        if self.is_file:
            source = self.source
            return Path(source.name)
        else:
            raise ValueError("Buffer does not correspond to the file.")


    @property
    def is_normal_type(self) -> bool:
        """Expose implementation's `is_normal_type` property.
        Specifically, return whether the buffer is regarded as editable by pytoy.
        """
        return self.impl.is_normal_type

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

    @property
    def lines(self) -> list[str]:
        return self._impl.lines

    def show(self):
        return self._impl.show()

    def hide(self):
        return self._impl.hide()

    def get_lines(self, line_range: LineRange) -> list[str]:
        return self.range_operator.get_lines(line_range)

    def get_text(self, character_range: CharacterRange) -> str:
        return self.range_operator.get_text(character_range)

    def replace_text(self, character_range: CharacterRange, text: str) -> CharacterRange:
        return self.range_operator.replace_text(character_range, text)

    @property
    def range_operator(self) -> RangeOperatorProtocol:
        return self.impl.range_operator
    
    def get_windows(self, only_visible: bool = True) -> Sequence["PytoyWindow"]:
        from pytoy.shared.ui.pytoy_window import PytoyWindow
        return [PytoyWindow(item) for item in self.impl.get_windows(only_visible=only_visible)]
        
    @property
    def window(self) -> "PytoyWindow | None":
        windows = self.get_windows()
        if windows:
            return windows[0]
        windows  = self.get_windows(only_visible=False)
        if windows:
            return windows[0]
        return None
    

class PytoyBufferProvider(PytoyBufferProviderProtocol):
    def __init__(self, impl: PytoyBufferProviderProtocol | None = None):
        self._impl = impl or _get_provider_impl()
        
    @property
    def impl(self) -> PytoyBufferProviderProtocol:
        return self._impl

    def get_buffers(self, is_normal_type: bool = True) -> Sequence[PytoyBuffer]:
        return [PytoyBuffer(elem) for elem in self.impl.get_buffers(is_normal_type=is_normal_type)]

    def get_current(self) -> PytoyBuffer:
        return PytoyBuffer(self.impl.get_current())

    def query(self, query: BufferQuery | BufferSource) -> Sequence[PytoyBuffer]:
        if isinstance(query, BufferSource):
            query = BufferQuery.from_source(query)
        buffers = self.get_buffers(query.is_normal_type)
        buffer_sources = query.buffer_sources
        if buffer_sources is None:
            return buffers
        else:
            result = []
            for source in buffer_sources:
                print("buffers-sources", [elem.source for elem in buffers])
                print("source", source)
                result += [elem for elem in buffers if elem.source == source]
            return result


def make_buffer(stdout_name: str, mode: Literal["vertical", "horizontal"] = "vertical") -> PytoyBuffer:
    from pytoy.shared.ui.pytoy_window import PytoyWindowProvider
    from pytoy.shared.ui.pytoy_window.models import WindowCreationParam

    param = WindowCreationParam.for_split("vertical", try_reuse=True, anchor=None)
    stdout_window = PytoyWindowProvider().open_window(stdout_name, param)
    return stdout_window.buffer


def make_duo_buffers(
    stdout_name: str, stderr_name: str
) -> tuple[PytoyBuffer, PytoyBuffer]:
    """Create 2 buffers, which is intended to `STDOUT` and `STDERR`."""

    from pytoy.shared.ui.pytoy_window import PytoyWindowProvider
    from pytoy.shared.ui.pytoy_window.models import WindowCreationParam
    

    provider = PytoyWindowProvider()
    param = WindowCreationParam.for_split("vertical", try_reuse=True, anchor=None)
    stdout_window = provider.open_window(stdout_name, param)

    param = WindowCreationParam.for_split("horizontal", try_reuse=True, anchor=stdout_window)
    stderr_window = provider.open_window(stderr_name, param)
    
    return (stdout_window.buffer, stderr_window.buffer)


def _get_provider_impl() -> PytoyBufferProviderProtocol:
    from pytoy.shared.lib.backend import get_backend_enum, BackendEnum
    backend_enum = get_backend_enum()
    if backend_enum == BackendEnum.VSCODE:
        from pytoy.shared.ui.pytoy_buffer.impls.vscode import PytoyBufferProviderVSCode
        impl = PytoyBufferProviderVSCode()
    elif backend_enum in (BackendEnum.VIM, BackendEnum.NVIM):
        from pytoy.shared.ui.pytoy_buffer.impls.vim import PytoyBufferProviderVim
        impl = PytoyBufferProviderVim()
    else:
        from pytoy.shared.ui.pytoy_buffer.impls.dummy import PytoyBufferProviderDummy
        impl = PytoyBufferProviderDummy()
    return impl


if __name__ == "__main__":
    pass
