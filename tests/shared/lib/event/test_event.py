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


def test_once_only_notifies_listener_once() -> None:
    emitter = EventEmitter[int]()
    values: list[int] = []

    emitter.event.once().subscribe(values.append)
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
