import pytest

from pytoy.shared.lib.event import EventEmitter


def test_subscribe_receives_fired_values() -> None:
    emitter = EventEmitter[int]()
    values: list[int] = []

    emitter.event.subscribe(values.append)
    emitter.fire(1)
    emitter.fire(2)

    assert values == [1, 2]


def test_disposable_stops_listener_and_is_idempotent() -> None:
    emitter = EventEmitter[int]()
    values: list[int] = []
    disposable = emitter.event.subscribe(values.append)

    disposable.dispose()
    disposable.dispose()
    emitter.fire(1)

    assert values == []


def test_subscriptions_added_during_emission_start_on_next_emission() -> None:
    emitter = EventEmitter[int]()
    values: list[str] = []
    added = False

    def listener(value: int) -> None:
        nonlocal added
        values.append("original")
        if not added:
            added = True
            emitter.event.subscribe(lambda _: values.append("new"))

    emitter.event.subscribe(listener)
    emitter.fire(1)
    assert values == ["original"]

    emitter.fire(2)
    assert values.count("original") == 2
    assert values.count("new") == 1


def test_once_only_notifies_listener_once() -> None:
    emitter = EventEmitter[int]()
    values: list[int] = []

    emitter.event.once().subscribe(values.append)
    emitter.fire(1)
    emitter.fire(2)

    assert values == [1]


def test_once_is_consumed_before_reentrant_emission() -> None:
    emitter = EventEmitter[int]()
    values: list[int] = []

    def listener(value: int) -> None:
        values.append(value)
        if value == 1:
            emitter.fire(2)

    emitter.event.once().subscribe(listener)
    emitter.fire(1)

    assert values == [1]


def test_once_is_consumed_when_listener_raises() -> None:
    emitter = EventEmitter[int]()
    values: list[int] = []

    def listener(value: int) -> None:
        values.append(value)
        if value == 1:
            raise RuntimeError("expected")

    emitter.event.once().subscribe(listener)
    with pytest.raises(RuntimeError, match="expected"):
        emitter.fire(1)
    emitter.fire(2)

    assert values == [1]


def test_map_transforms_values() -> None:
    emitter = EventEmitter[int]()
    values: list[str] = []

    emitter.event.map(str).subscribe(values.append)
    emitter.fire(3)

    assert values == ["3"]


def test_filter_only_notifies_for_matching_values() -> None:
    emitter = EventEmitter[int]()
    values: list[int] = []

    emitter.event.filter(lambda value: value % 2 == 0).subscribe(values.append)
    emitter.fire(1)
    emitter.fire(2)
    emitter.fire(4)

    assert values == [2, 4]


def test_event_can_be_used_as_a_decorator() -> None:
    emitter = EventEmitter[str]()
    values: list[str] = []

    @emitter.event
    def listener(value: str) -> None:
        values.append(value)

    emitter.fire("ready")

    assert values == ["ready"]


def test_emitter_dispose_stops_all_listeners() -> None:
    emitter = EventEmitter[int]()
    values: list[int] = []

    emitter.event.subscribe(values.append)
    emitter.dispose()
    emitter.fire(1)

    assert values == []


def test_emitter_dispose_is_idempotent_and_allows_later_subscriptions() -> None:
    emitter = EventEmitter[int]()
    values: list[int] = []

    emitter.event.subscribe(lambda value: values.append(-value))
    emitter.dispose()
    emitter.dispose()
    emitter.event.subscribe(values.append)
    emitter.fire(1)

    assert values == [1]
