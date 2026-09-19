import pytest

from pytoy.shared.ui.pytoy_quickfix import (
    BackendQuickfixViewer,
    PytoyQuickfixViewer,
    Quickfix,
    QuickfixRecord,
)
from pytoy.shared.ui.pytoy_quickfix.manager import QuickfixEntityManager
from pytoy.shared.ui.pytoy_quickfix.models import QuickfixQuery


def make_records() -> list[QuickfixRecord]:
    return [
        QuickfixRecord(filename="first.py", lnum=1, text="first"),
        QuickfixRecord(filename="second.py", lnum=2, text="second"),
    ]


def test_quickfix_starts_empty() -> None:
    quickfix = Quickfix.create(entity_manager=QuickfixEntityManager())

    assert quickfix.records == []
    assert quickfix.current_record is None


def test_quickfix_navigates_records_and_wraps() -> None:
    quickfix = Quickfix.create(entity_manager=QuickfixEntityManager())
    records = make_records()

    quickfix.set_records(records)

    assert quickfix.records == records
    assert quickfix.current_record == records[0]
    assert quickfix.next() == records[1]
    assert quickfix.next() == records[0]
    assert quickfix.prev() == records[1]


def test_quickfix_clear_removes_records_and_selection() -> None:
    quickfix = Quickfix.create(entity_manager=QuickfixEntityManager())
    quickfix.set_records(make_records())

    quickfix.clear()

    assert quickfix.records == []
    assert quickfix.current_record is None


def test_quickfix_provides_public_viewer_adapters() -> None:
    quickfix = Quickfix.create(entity_manager=QuickfixEntityManager())

    assert isinstance(quickfix.provide_ui("pytoy"), PytoyQuickfixViewer)
    assert isinstance(quickfix.provide_ui("backend"), BackendQuickfixViewer)


def test_quickfix_get_or_create_reuses_existing_quickfix_in_given_manager() -> None:
    manager = QuickfixEntityManager()
    existing = Quickfix.create(kind="named", entity_manager=manager)
    existing.set_records(make_records())

    quickfix = Quickfix.get_or_create(kind="named", entity_manager=manager)

    assert quickfix.records == existing.records
    assert manager.current is not None
    assert manager.current.records == existing.records


def test_quickfix_manager_creates_and_tracks_named_quickfixes() -> None:
    manager = QuickfixEntityManager()

    default = manager.create()
    named = manager.create("named")

    assert manager.get(default.id) is default
    assert manager.get(named.id) is named
    assert manager.current is default


def test_quickfix_manager_query_filters_by_kind() -> None:
    manager = QuickfixEntityManager()
    errors = manager.create("errors")
    manager.create("warnings")

    assert manager.query(QuickfixQuery.from_any(kind="errors")) == (errors,)
    assert manager.query() == tuple(manager.query(QuickfixQuery.from_any()))


def test_quickfix_manager_changes_and_removes_current_quickfix() -> None:
    manager = QuickfixEntityManager()
    default = manager.create()
    named = manager.create("named")

    assert manager.set_current(named.id) is named
    assert manager.current is named

    assert manager.remove(named.id) is named
    assert manager.current is default


def test_quickfix_manager_rejects_duplicate_entity_ids() -> None:
    manager = QuickfixEntityManager()
    entity = manager.create("named")

    with pytest.raises(ValueError):
        manager.register(entity)
