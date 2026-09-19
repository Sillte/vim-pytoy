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
from pytoy.shared.ui.pytoy_quickfix.models import QuickfixQuery
from pytoy.shared.ui.pytoy_quickfix.viewers import QUICKFIX_UI_KIND, BackendQuickfixViewer, PytoyQuickfixViewer


class Quickfix:
    def __init__(self, *, entity: QuickfixEntity) -> None:
        self._entity = entity

    @staticmethod
    def _get_entity_manager(entity_manager: QuickfixEntityManager | None) -> QuickfixEntityManager:
        return entity_manager or GlobalPytoyContext.get().quickfix_entity_manager

    @classmethod
    def _from_entity(
        cls,
        entity: QuickfixEntity,
        *,
        entity_manager: QuickfixEntityManager,
        current_update: bool,
    ) -> Self:
        if current_update:
            entity_manager.set_current(entity.id)
        return cls(entity=entity)

    @staticmethod
    def _find_by_kind(kind: str, entity_manager: QuickfixEntityManager) -> QuickfixEntity | None:
        if entities := entity_manager.query(QuickfixQuery.from_any(kind=kind)):
            return entities[0]
        return None

    @classmethod
    def current(cls, *, entity_manager: QuickfixEntityManager | None = None) -> Self:
        entity_manager = cls._get_entity_manager(entity_manager)
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
        entity_manager = cls._get_entity_manager(entity_manager)
        entity = entity_manager.create(kind=kind, owner_end=owner_end, working_directory=working_directory)
        return cls._from_entity(entity, entity_manager=entity_manager, current_update=current_update)

    @classmethod
    def get_or_create(
        cls,
        *,
        kind: str = "$default",
        owner_end: Event | None = None,
        working_directory: Path | None = None,
        current_update: bool = True,
        entity_manager: QuickfixEntityManager | None = None,
    ) -> Self:

        if quickfix := cls.get_from_kind(
            kind=kind,
            current_update=current_update,
            entity_manager=entity_manager,
        ):
            return quickfix
        return cls.create(
            kind=kind,
            owner_end=owner_end,
            working_directory=working_directory,
            current_update=current_update,
            entity_manager=entity_manager,
        )

    @classmethod
    def get_from_kind(
        cls,
        kind: str,
        current_update: bool = True,
        *,
        entity_manager: QuickfixEntityManager | None = None,
    ) -> Self | None:
        entity_manager = cls._get_entity_manager(entity_manager)
        entity = cls._find_by_kind(kind, entity_manager)
        if entity is None:
            return None
        return cls._from_entity(entity, entity_manager=entity_manager, current_update=current_update)

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
        entity_manager = cls._get_entity_manager(entity_manager)
        entity = None
        if try_reuse:
            entity = cls._find_by_kind(kind, entity_manager)
        if entity is None:
            entity = entity_manager.create(kind=kind, owner_end=owner_end, working_directory=working_directory)
        entity.set_records(records)
        return cls._from_entity(entity, entity_manager=entity_manager, current_update=current_update)

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
