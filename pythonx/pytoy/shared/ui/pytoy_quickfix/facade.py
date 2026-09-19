import re
from pathlib import Path
from typing import Callable, Literal, Self, Sequence, assert_never, overload

from pytoy.contexts.pytoy import GlobalPytoyContext
from pytoy.shared.lib.backend import BackendEnum, get_backend_enum
from pytoy.shared.lib.event import Event
from pytoy.shared.ui.contract.quickfix import (
    PytoyQuickfixProtocol,
    QuickfixRecord,
    QuickfixState,
    QuickfixViewerProtocol,
)
from pytoy.shared.ui.pytoy_quickfix.entity import QuickfixEntity, QuickfixEntityID, QuickfixEntityQuery
from pytoy.shared.ui.pytoy_quickfix.manager import QuickfixEntityManager
from pytoy.shared.ui.pytoy_quickfix.service import PytoyQuickfixService
from pytoy.shared.ui.pytoy_quickfix.state_resolvers import PytoyQuickfixStateResolver

from .viewer import PytoyQuickfixViewer

type QUICKFIX_UI_KIND = Literal["pytoy", "backend"]


class BackendQuickfixViewer:
    def __init__(self, entity: QuickfixEntity, *, impl: QuickfixViewerProtocol) -> None:
        self._entity = entity
        self._impl = impl

    @classmethod
    def create(
        cls,
        entity: QuickfixEntity,
    ) -> Self:
        impl = _create_backend_viewer(entity)
        return cls(entity=entity, impl=impl)

    def show(self) -> None:
        self._impl.show()

    def close(self) -> None:
        self._impl.close()

    def sync_to_ui(self, only_index: bool = True) -> None:
        self._impl.sync_to_ui(only_index=only_index)

    def sync_from_ui(self, only_index: bool = True) -> None:
        self._impl.sync_from_ui(only_index=only_index)

    def jump(self, *, with_focus: bool = False) -> QuickfixRecord | None:
        return self._impl.jump(with_focus=with_focus)


def _create_backend_viewer(entity: QuickfixEntity) -> QuickfixViewerProtocol:
    backend = get_backend_enum()

    def make_vim():
        from pytoy.shared.ui.pytoy_quickfix.impls.vim import QuickfixVimViewer

        return QuickfixVimViewer(entity=entity)

    def make_vscode():
        from pytoy.shared.ui.pytoy_quickfix.impls.vscode import QuickfixVSCodeViewer

        return QuickfixVSCodeViewer(entity=entity)

    def make_dummy():
        from pytoy.shared.ui.pytoy_quickfix.impls.dummy import QuickfixDummyViewer

        return QuickfixDummyViewer(entity=entity)

    creators = {
        BackendEnum.VSCODE: make_vscode,
        BackendEnum.DUMMY: make_dummy,
        BackendEnum.VIM: make_vim,
        BackendEnum.NVIM: make_vim,
    }
    return creators[backend]()


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
    def on_end(self) -> Event[QuickfixEntityID]:
        return self._entity.on_end


class PytoyQuickfix:
    def __init__(
        self,
        impl: PytoyQuickfixProtocol | None = None,
        *,
        name: str | None = "$default",
    ):
        if impl is None:
            if name is None:
                raise ValueError("impl or name must be set.")
            impl = _get_service(name)
        self._impl = impl

    @property
    def impl(self) -> PytoyQuickfixProtocol:
        return self._impl

    def handle_records(self, records: Sequence[QuickfixRecord], is_open: bool = False) -> QuickfixState | None:
        if records:
            state = self.set_records(records)
            if is_open:
                self.open()
            return state
        self.close()
        return None

    def set_records(self, records: Sequence[QuickfixRecord]) -> QuickfixState:
        return self.impl.set_records(records)

    @property
    def records(self) -> Sequence[QuickfixRecord]:
        return self.impl.records

    @property
    def state(self) -> QuickfixState | None:
        return self.impl.state

    def close(self) -> None:
        return self.impl.close()

    def open(self) -> None:
        return self.impl.open()

    def jump(self, state: int | QuickfixState | None = None) -> QuickfixRecord | None:
        return self.impl.jump(state)

    def move(self, diff_index: int) -> QuickfixRecord | None:
        return self.impl.move(diff_index)

    def next(self) -> QuickfixRecord | None:
        return self.move(+1)

    def prev(self) -> QuickfixRecord | None:
        return self.move(-1)


_quickfix_cache = dict()


def _get_service(name: str) -> PytoyQuickfixProtocol:
    if name in _quickfix_cache:
        return _quickfix_cache[name]

    backend_enum = get_backend_enum()

    def make_vscode():
        from pytoy.shared.ui.pytoy_quickfix.impls.vscode import PytoyQuickfixVSCodeUI

        return PytoyQuickfixService(PytoyQuickfixStateResolver(), PytoyQuickfixVSCodeUI())

    def make_vim():
        from pytoy.shared.ui.pytoy_quickfix.impls.vim import PytoyQuickfixVimUI

        return PytoyQuickfixService(PytoyQuickfixStateResolver(), PytoyQuickfixVimUI())

    def make_dummy():
        from pytoy.shared.ui.pytoy_quickfix.impls.dummy import PytoyQuickfixDummyUI

        return PytoyQuickfixService(PytoyQuickfixStateResolver(), PytoyQuickfixDummyUI())

    creators = {
        BackendEnum.VSCODE: make_vscode,
        BackendEnum.VIM: make_vim,
        BackendEnum.NVIM: make_vim,
        BackendEnum.DUMMY: make_dummy,
    }
    _quickfix_cache[name] = creators[backend_enum]()
    return _quickfix_cache[name]


def get_pytoy_quickfix(name: str) -> PytoyQuickfix:
    return PytoyQuickfix(_get_service(name))


def handle_records(
    pytoy_quickfix: PytoyQuickfix,
    records: Sequence[QuickfixRecord],
    is_open: bool = True,
):
    """When `records` are given, `PytoyQuickfix` handles them."""
    if records:
        pytoy_quickfix.set_records(records)
        if is_open:
            pytoy_quickfix.open()
    else:
        pytoy_quickfix.close()


type QuickfixRecordRegex = str
type QuickfixCreator = Callable[[str, Path], Sequence[QuickfixRecord]]


def to_quickfix_creator(regex: QuickfixRecordRegex | QuickfixCreator) -> QuickfixCreator:
    if isinstance(regex, str):
        pattern = re.compile(regex)

        def creator_impl(content: str, cwd: Path) -> Sequence[QuickfixRecord]:
            records = []
            for line in content.split("\n"):
                match = pattern.match(line)
                if match:
                    records.append(QuickfixRecord.from_dict(match.groupdict(), cwd))
            return records

        return creator_impl
    return regex
