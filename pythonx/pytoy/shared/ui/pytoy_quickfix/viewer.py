from pytoy.shared.ui.pytoy_quickfix.protocol import PytoyQuickfixProtocol
from pytoy.shared.ui.pytoy_quickfix.models import QuickfixRecord
from pytoy.shared.ui.pytoy_buffer import PytoyBuffer, PytoyBufferProvider, BufferQuery, BufferSource, make_buffer, LineRange
from pytoy.shared.ui.pytoy_window import PytoyWindow, CursorPosition, PytoyWindowProvider, WindowCreationParam
from typing import Final 
from pathlib import Path
import re


_CACHE = dict()
class QuickfixViewer:
    BUFFER_NAME: Final[str] = "__pytoy_quickfix__"

    def __init__(self, quickfix: PytoyQuickfixProtocol) -> None:
        self._quickfix = quickfix

    @property
    def quickfix(self) -> PytoyQuickfixProtocol:
        return self._quickfix
    

    def open_viewer(self):
        viewer_buffer = self._get_record_buffer()
        viewer_buffer.init_buffer()

        records = self.quickfix.records
        for index, record in enumerate(records):
            line = self._record_to_text(record, index)
            viewer_buffer.append(line)
        viewer_buffer.actions["<CR>"].subscribe(lambda _: self.on_enter())
        from pytoy.shared.lib.keymap.keymap_manager import KeymapManager, KeymapSpec
        #from pytoy.contexts.vim import GlobalVimContext
        #keymap_manager = GlobalVimContext.get().keymap_manager
        
    
    
    def on_enter(self):
        buffer = self._get_record_buffer()
        current_window = PytoyWindow.get_current()
        if current_window.buffer.source != buffer.source:
            raise ValueError("Quickfix buffer is not active.")
        cursor = current_window.cursor
        line = cursor.line
        text = "".join(buffer.get_lines(LineRange(line, line + 1)))
        index = self._text_to_index(text)
        record = self.quickfix.records[index]
        window = self._get_destination_window()
        provider = PytoyWindowProvider()

        position = CursorPosition(line=record.lnum, col=0)
        source = BufferSource(type="file", name=record.filename)
        param = WindowCreationParam(cursor=position, target="in-place", anchor=window)
        window = provider.open_window(source=source, param=param)
        window.focus()

        
    def _record_to_text(self, record: QuickfixRecord, index: int) -> str:
        filename = Path(record.filename).name
        return f"{filename}:{record.lnum}:{record.text}${index}"


    def _text_to_index(self, line: str) -> int:
        _INDEX_PATTERN = re.compile(r"\$(?P<index>\d+)$")
        match = _INDEX_PATTERN.search(line)
        if match is None:
            raise ValueError(f"Cannot extract quickfix index from: {line!r}")
        return int(match.group("index"))
    
    def _get_destination_window(self) -> PytoyWindow:
        windows = PytoyWindow.get_windows()
        for window in windows:
            if window.is_left() and window.buffer.is_file:
                return window
        return PytoyWindow.get_current()

            

        
    def _get_record_buffer(self, ) -> PytoyBuffer:
        provider = PytoyBufferProvider()
        source = BufferSource(type="nofile", name=self.BUFFER_NAME)
        query = BufferQuery(buffer_sources=[source])
        buffers = provider.query(query)
        if buffers:
            buffer = buffers[0]
        else:
            buffer = make_buffer(source, mode="vertical")
        return buffer
        
    
    def _is_viewer_buffer(self, buffer: PytoyBuffer | None = None) -> bool:
        try:
            buffer = buffer or PytoyBuffer.get_current()
            source = buffer.source
        except Exception:
            return False
        return source.type == "nofile" and source.name == self.BUFFER_NAME


    def _is_main_window(self, window: PytoyWindow | None = None) -> bool:
        window = window or PytoyWindow.get_current()
        return window.is_left()


