from pathlib import Path
from typing import Literal, Self, Sequence, assert_never, overload

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.shared.lib.event import Event
from pytoy.shared.ui.contract.quickfix import (
    QuickfixRecord,
    QuickfixState,
)
from pytoy.shared.ui.pytoy_quickfix.entity import QuickfixEntity, QuickfixID
from pytoy.shared.ui.pytoy_quickfix.manager import QuickfixEntityManager
from pytoy.shared.ui.pytoy_quickfix.models import QuickfixEntityQuery
from pytoy.shared.ui.pytoy_quickfix.viewers import QUICKFIX_UI_KIND, BackendQuickfixViewer, PytoyQuickfixViewer


class Quickfix:
    def __init__(self, *, entity: QuickfixEntity) -> None:
        self._entity = entity

    @classmethod
    def current(cls, *, entity_manager: QuickfixEntityManager | None = None) -> Self:
        entity_manager = entity_manager or GlobalPytoyContext.get().quickfix_entity_manager
        entity = entity_manager.current
        if entity is None:
            raise ValueError("No current Quickfix entity.")
        return cls(entity=entity)

    @classmethod
    def create(
        cls,
        *,
        kind: str = "$default",
        owner_end: Event | None = None,
        working_directory: Path | None = None,
        current_update: bool = True,
        entity_manager: QuickfixEntityManager | None = None,
    ) -> Self:
        entity_manager = entity_manager or GlobalPytoyContext.get().quickfix_entity_manager
        entity = entity_manager.create(kind=kind, owner_end=owner_end, working_directory=working_directory)
        if current_update:
            entity_manager.set_current(entity.id)
        return cls(entity=entity)

    @classmethod
    def from_any(
        cls,
        records: Sequence[QuickfixRecord],
        kind: str = "$default",
        owner_end: Event | None = None,
        try_reuse: bool = False,
        working_directory: Path | None = None,
        current_update: bool = True,
        *,
        entity_manager: QuickfixEntityManager | None = None,
    ) -> Self:
        entity_manager = entity_manager or GlobalPytoyContext.get().quickfix_entity_manager
        if try_reuse:
            if entities := entity_manager.query(QuickfixEntityQuery.from_any(kind=kind)):
                entity = entities[0]
                entity.set_records(records)
                quickfix = cls(entity=entity)
                if current_update:
                    entity_manager.set_current(entity.id)
                return quickfix
        entity = entity_manager.create(kind=kind, owner_end=owner_end, working_directory=working_directory)
        entity.set_records(records)
        if current_update:
            entity_manager.set_current(entity.id)
        return cls(entity=entity)

    @property
    def kind(self) -> str:
        return self._entity.kind

    def set_records(self, records: Sequence[QuickfixRecord]) -> None:
        self._entity.set_records(records)

    def clear(self) -> None:
        self._entity.clear()

    @property
    def records(self) -> Sequence[QuickfixRecord]:
        return self._entity.records

    @property
    def state(self) -> QuickfixState:
        return self._entity.state

    @property
    def current_record(self) -> QuickfixRecord | None:
        return self._entity.current_record

    def select(self, index: int) -> QuickfixRecord | None:
        return self._entity.select(index)

    def move(self, diff_index: int) -> QuickfixRecord | None:
        return self._entity.move(diff_index)

    def next(self) -> QuickfixRecord | None:
        return self._entity.next()

    def prev(self) -> QuickfixRecord | None:
        return self._entity.prev()

    def dispose(self) -> None:
        self._entity.dispose()

    @overload
    def provide_ui(self, ui_kind: Literal["backend"]) -> BackendQuickfixViewer: ...
    @overload
    def provide_ui(self, ui_kind: Literal["pytoy"]) -> PytoyQuickfixViewer: ...
    def provide_ui(self, ui_kind: QUICKFIX_UI_KIND) -> BackendQuickfixViewer | PytoyQuickfixViewer:
        match ui_kind:
            case "backend":
                return BackendQuickfixViewer.create(entity=self._entity)
            case "pytoy":
                return PytoyQuickfixViewer.create(entity=self._entity)
            case _:
                assert_never(ui_kind)

    @property
    def on_end(self) -> Event[QuickfixID]:
        return self._entity.on_end


type PytoyQuickfix = Quickfix
