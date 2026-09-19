import re
from pathlib import Path
from typing import Final, Self

from pytoy.shared.lib.text import CursorPosition, LineRange
from pytoy.shared.ui.contract.quickfix import QuickfixRecord, QuickfixViewerProtocol
from pytoy.shared.ui.pytoy_buffer import (
    BufferQuery,
    BufferSource,
    PytoyBuffer,
    PytoyBufferProvider,
)
from pytoy.shared.ui.pytoy_window import PytoyWindow, PytoyWindowProvider, WindowCreationParam

from .entity import QuickfixEntity


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


class PytoyQuickfixViewer(QuickfixViewerProtocol):
    BUFFER_NAME: Final[str] = "__pytoy_quickfix__"

    def __init__(self, entity: QuickfixEntity) -> None:
        self._entity = entity
        self._line_codec = _LineCodec()
        self._file_window_selector = _FileWindowSelector()
        self._quickfix_buffer_provider = _QuickfixBufferProvider(self.BUFFER_NAME)

    @classmethod
    def create(cls, entity: QuickfixEntity) -> Self:
        return cls(entity=entity)

    def show(self) -> None:
        self.sync_to_ui(only_index=False)
        q_buffer = self._quickfix_buffer_provider.provide()

        disposables_key = "quickfix-event-disposables"
        for disposable in q_buffer.metadata.data.get(disposables_key, []):
            disposable.dispose()

        disposables = []
        disposables.append(q_buffer.actions["<CR>"].subscribe(lambda _: self.jump(with_focus=True)))
        disposables.append(q_buffer.actions["<SPACE>"].subscribe(lambda _: self.jump(with_focus=False)))
        q_buffer.metadata.data[disposables_key] = disposables

    def close(self) -> None:
        q_buffer = self._quickfix_buffer_provider.provide()
        disposables_key = "quickfix-event-disposables"
        for disposable in q_buffer.metadata.data.pop(disposables_key, []):
            disposable.dispose()

    def sync_to_ui(self, only_index: bool = True) -> None:
        q_buffer = self._quickfix_buffer_provider.provide()
        if not only_index:
            records = self._entity.records
            lines = "\n".join([self._line_codec.encode(record, index) for index, record in enumerate(records)])
            q_buffer.init_buffer(lines)

    def sync_from_ui(self, only_index: bool = True) -> None:
        current_window = PytoyWindow.get_current()
        q_buffer = self._quickfix_buffer_provider.provide()
        if current_window.buffer.source != q_buffer.source:
            raise ValueError(
                f"Current window does not handle `QuickfixBuffer`. `{current_window.buffer.source=}`, "
                f"`{q_buffer.source=}`"
            )
        cursor = current_window.cursor
        text = "".join(q_buffer.get_lines(LineRange(cursor.line, cursor.line + 1)))
        self._entity.select(self._line_codec.decode(text))

    def jump(self, *, with_focus: bool = False) -> QuickfixRecord | None:
        current_window = PytoyWindow.get_current()
        q_buffer = self._quickfix_buffer_provider.provide()
        if current_window.buffer.source != q_buffer.source:
            raise ValueError(
                f"Current window does not handle `QuickfixBuffer`. `{current_window.buffer.source=}`, `{q_buffer.source=}`"
            )
        cursor = current_window.cursor
        line = cursor.line
        text = "".join(q_buffer.get_lines(LineRange(line, line + 1)))
        index = self._line_codec.decode(text)
        record = self._entity.select(index)
        if record is None:
            return None
        window = self._file_window_selector.select()

        provider = PytoyWindowProvider()
        position = CursorPosition(line=record.lnum - 1, col=0)
        source = BufferSource(type="file", name=record.filename)
        param = WindowCreationParam(cursor=position, target="in-place", anchor=window)
        window = provider.open_window(source=source, param=param)
        if with_focus:
            window.focus()
        return record
