from pathlib import Path
from typing import Sequence

import vim

from pytoy.shared.ui.contract.buffer.models import BufferSource
from pytoy.shared.ui.contract.quickfix import (
    PytoyQuickfixUIProtocol,
    QuickfixRecord,
    QuickfixState,
    QuickfixViewerProtocol,
)
from pytoy.shared.ui.pytoy_quickfix.entity import QuickfixEntity
from pytoy.shared.ui.pytoy_window import PytoyWindowProvider, WindowCreationParam


class PytoyQuickfixVSCodeUI(PytoyQuickfixUIProtocol):
    def __init__(
        self,
    ):
        self._records = []
        self._index = None

    def set_records(self, records: Sequence[QuickfixRecord]) -> QuickfixState:
        self._records = records
        self._index = self._index if self._index else 0
        return QuickfixState(index=self._index, size=len(self._records))

    def open(self) -> None:
        # We have to consider how to display in vscode.
        pass

    def close(self) -> None:
        # We have to consider how to display in vscode.
        pass

    def jump(self, state: QuickfixState) -> QuickfixRecord | None:
        if not self._records:
            return None
        if state.index is None:
            raise ValueError("State is invalid.")
        record = self._records[state.index]
        self._index = state.index

        path = Path(record.filename)
        cursor = record.cursor
        param = WindowCreationParam.for_in_place(try_reuse=False, anchor=None, cursor=cursor)
        PytoyWindowProvider().open_window(BufferSource.from_path(path), param)
        return record

    @property
    def records(self) -> Sequence[QuickfixRecord]:
        # When the UI modification is implemented,
        # this is the connection point.
        return self._records

    @property
    def state(self) -> QuickfixState | None:
        return QuickfixState(self._index, len(self._records))


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
