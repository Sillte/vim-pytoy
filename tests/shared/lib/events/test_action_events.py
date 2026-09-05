from pytoy.shared.lib.events.action_events import KeyActionEvents, KeyEventManager
from pytoy.shared.lib.events.domain.action import KeySequence
from pytoy.shared.lib.events.impls.dummy.action_events import DummyKeyEventManager


def create_manager() -> KeyEventManager:
    return KeyEventManager(DummyKeyEventManager())


def test_clear_removes_all_specs_for_buffer() -> None:
    manager = create_manager()
    actions = KeyActionEvents(1, manager=manager)
    other_actions = KeyActionEvents(1, manager=manager)
    other_buffer_actions = KeyActionEvents(2, manager=manager)
    global_actions = KeyActionEvents(None, manager=manager)

    actions[KeySequence("a")]
    other_actions[KeySequence("b")]
    other_buffer_actions[KeySequence("c")]
    global_actions[KeySequence("d")]

    actions.clear()

    assert {(spec.key, spec.buffer) for spec in manager.specs} == {
        (KeySequence("c"), 2),
        (KeySequence("d"), None),
    }
