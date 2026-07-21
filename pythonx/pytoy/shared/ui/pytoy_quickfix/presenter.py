from pytoy.shared.ui.pytoy_quickfix.protocol import PytoyQuickfixProtocol
from pytoy.shared.ui.pytoy_quickfix.models import QuickfixRecord
from pytoy.shared.ui.pytoy_buffer import (
    PytoyBuffer,
    PytoyBufferProvider,
    BufferQuery,
    BufferSource,
    make_buffer,
    LineRange,
)
from pytoy.shared.ui.pytoy_window import PytoyWindow, CursorPosition, PytoyWindowProvider, WindowCreationParam
from typing import Final
from pathlib import Path
import re


class _LineCodec:
    INDEX_PATTERN = re.compile(r"\$(?P<index>\d+)$")

    def encode(self, record: QuickfixRecord, index: int) -> str:
        filename = Path(record.filename).name
        return f"{filename}:{record.lnum}:{record.text}${index}"

    def decode(self, line: str) -> int:
        """Return `index`."""
        match = self.INDEX_PATTERN.search(line)
        if match is None:
            raise ValueError(f"Cannot extract quickfix index from: {line!r}")
        return int(match.group("index"))
    
class _FileWindowSelector:
    def __init__(self):
        pass
        
    def select(self) -> PytoyWindow:
        windows = PytoyWindow.get_windows()
        for window in windows:
            if window.is_left() and window.buffer.is_file:
                return window
        return PytoyWindow.get_current()
    
class _QuickfixBufferProvider:
    def __init__(self, buffer_name: str):
        self._buffer_name = buffer_name
    @property
    def buffer_name(self) -> str:
        return self._buffer_name
    
    def provide(self) -> PytoyBuffer: 
        provider = PytoyBufferProvider()
        source = BufferSource(type="nofile", name=self.buffer_name)
        query = BufferQuery(buffer_sources=[source])
        buffers = provider.query(query)
        if buffers:
            buffer = buffers[0]
            for buffer in buffers:
                if buffer.get_windows():
                    return buffer

        provider = PytoyWindowProvider()
        window = provider.get_current()
        if window.is_left():
            param = WindowCreationParam(target="split", split_direction="vertical")
        else:
            param = WindowCreationParam(target="in-place")
        window = provider.open_window(source, param)
        buffer = window.buffer
        return buffer



class QuickfixPresenter:
    BUFFER_NAME: Final[str] = "__pytoy_quickfix__"

    def __init__(self, quickfix: PytoyQuickfixProtocol) -> None:
        self._quickfix = quickfix
        self._line_codec = _LineCodec()
        self._file_window_selector = _FileWindowSelector()
        self._quickfix_buffer_provider = _QuickfixBufferProvider(self.BUFFER_NAME)

    @property
    def quickfix(self) -> PytoyQuickfixProtocol:
        return self._quickfix

    def show(self):
        q_buffer = self._quickfix_buffer_provider.provide()

        records = self.quickfix.records
        lines = "\n".join([self._line_codec.encode(record, index) for index, record in enumerate(records)])
        q_buffer.init_buffer(lines)
        q_buffer.actions["<CR>"].subscribe(lambda _: self.jump(with_focus=True))
        q_buffer.actions["<SPACE>"].subscribe(lambda _: self.jump(with_focus=False))

    def jump(self, with_focus: bool = True):
        current_window = PytoyWindow.get_current()
        q_buffer = self._quickfix_buffer_provider.provide()
        if current_window.buffer.source != q_buffer.source:
            raise ValueError("Current window does not handle `QuickfixBuffer`.")
        cursor = current_window.cursor
        line = cursor.line
        text = "".join(q_buffer.get_lines(LineRange(line, line + 1)))
        index = self._line_codec.decode(text)
        record = self.quickfix.records[index]
        window = self._file_window_selector.select()
        
        provider = PytoyWindowProvider()
        position = CursorPosition(line=record.lnum - 1, col=0)
        source = BufferSource(type="file", name=record.filename)
        param = WindowCreationParam(cursor=position, target="in-place", anchor=window)
        window = provider.open_window(source=source, param=param)
        if with_focus:
            window.focus()

