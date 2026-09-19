import pytest

from pytoy.shared.ui.pytoy_quickfix import Quickfix, QuickfixRecord
from pytoy.shared.ui.pytoy_quickfix.manager import QuickfixEntityManager


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


def test_quickfix_manager_creates_and_tracks_named_quickfixes() -> None:
    manager = QuickfixEntityManager()

    default = manager.create()
    named = manager.create("named")

    assert manager.get() is default
    assert manager.get("named") is named
    assert manager.current is default


def test_quickfix_manager_changes_and_replaces_current_quickfix() -> None:
    manager = QuickfixEntityManager()
    default = manager.create()
    named = manager.create("named")

    assert manager.set_current("named") is named
    assert manager.current is named

    updated = manager.update("named")

    assert updated is not named
    assert manager.get("named") is updated
    assert named.on_end is not updated.on_end

    assert manager.remove("named") is updated
    assert manager.current is default


def test_quickfix_manager_rejects_duplicate_names() -> None:
    manager = QuickfixEntityManager()
    manager.create("named")

    with pytest.raises(ValueError):
        manager.create("named")
