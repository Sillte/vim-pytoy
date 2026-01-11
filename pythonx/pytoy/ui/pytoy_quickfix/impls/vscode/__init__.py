from pathlib import Path
import vim
from typing import Sequence

from pytoy.infra.timertask import TimerTask
from pytoy.ui.pytoy_quickfix.protocol import  PytoyQuickfixUIProtocol
from pytoy.ui.pytoy_quickfix.models import QuickfixRecord, QuickfixState
from pytoy.ui.pytoy_window import PytoyWindowProvider, WindowCreationParam, BufferSource


class PytoyQuickfixVSCodeUI(PytoyQuickfixUIProtocol):

    def __init__(self, ):
        self._records = []
        self._index = None

    def set_records(self, records:  Sequence[QuickfixRecord]) -> QuickfixState:
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
        param = WindowCreationParam.for_in_place(try_reuse=True, anchor=None, cursor=cursor)
        PytoyWindowProvider().open_window(BufferSource.from_path(path), param)
        #TimerTask.execute_oneshot(lambda : window.move_cursor(cursor), interval=50)
        return record


    @property
    def records(self) -> Sequence[QuickfixRecord]:
        # When the UI modification is implemented,
        # this is the connection point.
        return self._records

    @property
    def state(self) -> QuickfixState | None:
        return QuickfixState(self._index, len(self._records))
