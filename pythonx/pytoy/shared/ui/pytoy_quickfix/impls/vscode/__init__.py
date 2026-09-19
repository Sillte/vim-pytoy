from pathlib import Path

from pytoy.shared.ui.contract.buffer.models import BufferSource
from pytoy.shared.ui.contract.quickfix import (
    QuickfixRecord,
    QuickfixViewerProtocol,
)
from pytoy.shared.ui.pytoy_quickfix.entity import QuickfixEntity
from pytoy.shared.ui.pytoy_window import PytoyWindowProvider, WindowCreationParam


class QuickfixVSCodeViewer(QuickfixViewerProtocol):
    def __init__(self, entity: QuickfixEntity) -> None:
        self._entity = entity

    def show(self) -> None:
        pass

    def close(self) -> None:
        pass

    def sync_to_ui(self, only_index: bool = True) -> None:
        pass

    def sync_from_ui(self, only_index: bool = True) -> None:
        pass

    def jump(self, *, with_focus: bool = False) -> QuickfixRecord | None:
        record = self._entity.current_record
        if record is None:
            return None
        path = Path(record.filename)
        cursor = record.cursor
        param = WindowCreationParam.for_in_place(try_reuse=False, anchor=None, cursor=cursor)
        window = PytoyWindowProvider().open_window(BufferSource.from_path(path), param)
        if with_focus:
            window.focus()
        return record
