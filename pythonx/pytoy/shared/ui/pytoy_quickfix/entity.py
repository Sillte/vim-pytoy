import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from pytoy.shared.lib.event import Event, EventEmitter
from pytoy.shared.ui.contract.quickfix import QuickfixRecord, QuickfixState

type QuickfixEntityID = str


@dataclass(frozen=True)
class QuickfixEntityQuery:
    kind: str | None = None

    @classmethod
    def from_any(cls, kind: str | None = None) -> Self:
        return cls(kind=kind)


class QuickfixEntity:
    def __init__(
        self, *, kind: str = "$default", owner_end: Event | None = None, working_directory: Path | None = None
    ) -> None:
        self._id = str(uuid.uuid4())
        self._kind = kind
        self._records: list[QuickfixRecord] = []
        self._index: int | None = None
        self._on_end_emitter = EventEmitter[str]()
        self._owner_disposable = owner_end.once().subscribe(lambda _: self.dispose()) if owner_end else None
        self._working_directory = working_directory
        self._disposed = False

    @property
    def id(self) -> QuickfixEntityID:
        return self._id

    @property
    def kind(self) -> str:
        return self._kind

    def set_records(self, records: Sequence[QuickfixRecord]) -> None:
        self._check_alive()
        self._records = list(records)
        self._index = 0 if self._records else None

    def clear(self) -> None:
        self._check_alive()
        self._records.clear()
        self._index = None

    @property
    def records(self) -> Sequence[QuickfixRecord]:
        return self._records

    @property
    def state(self) -> QuickfixState:
        return QuickfixState(index=self._index, size=len(self._records))

    def set_state(self, state: QuickfixState):
        self._check_alive()
        if state.index is None:
            self._index = None
        elif len(self._records) == 0:
            self._index = None
        else:
            self._index = state.index % len(self._records)

    @property
    def current_record(self) -> QuickfixRecord | None:
        if self._index is None:
            return None
        return self._records[self._index]

    def select(self, index: int) -> QuickfixRecord | None:
        self._check_alive()
        if not self._records:
            return None
        self._index = index % len(self._records)
        return self.current_record

    def move(self, diff_index: int) -> QuickfixRecord | None:
        self._check_alive()
        if self._index is None:
            return None
        return self.select(self._index + diff_index)

    def next(self) -> QuickfixRecord | None:
        return self.move(+1)

    def prev(self) -> QuickfixRecord | None:
        return self.move(-1)

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        if self._owner_disposable is not None:
            self._owner_disposable.dispose()
        self._on_end_emitter.fire(self.id)
        self._on_end_emitter.dispose()

    @property
    def working_directory(self) -> Path | None:
        return self._working_directory

    @property
    def on_end(self) -> Event[QuickfixEntityID]:
        return self._on_end_emitter.event

    def _check_alive(self) -> None:
        if self._disposed:
            raise RuntimeError("This is already disposed.")
