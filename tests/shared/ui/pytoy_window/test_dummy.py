import pytest

from pytoy.shared.ui.contract.buffer.models import BufferSource
from pytoy.shared.ui.contract.window.models import ViewportMoveMode
from pytoy.shared.ui.pytoy_buffer.impls.dummy import PytoyBufferDummy
from pytoy.shared.ui.pytoy_window.impls.dummy import PytoyWindowProviderDummy


@pytest.fixture
def provider():
    provider = PytoyWindowProviderDummy()
    previous_windows = provider._windows
    previous_counter = provider._counter
    provider._windows = []
    provider._counter = 0
    try:
        yield provider
    finally:
        provider._windows = previous_windows
        provider._counter = previous_counter


def test_close_invalidates_window_and_fires_event_once(provider: PytoyWindowProviderDummy) -> None:
    window = provider.open_window(BufferSource.from_no_file("close-test"))
    other = provider.open_window(BufferSource.from_no_file("other-test"))
    closed_ids: list[int] = []
    expected_id = provider._counter - 2
    window.on_closed.subscribe(closed_ids.append)

    assert window.close()
    assert window.close()

    assert not window.valid
    assert window not in provider._windows
    assert other in provider._windows
    assert closed_ids == [expected_id]


def test_unique_closes_other_windows(provider: PytoyWindowProviderDummy) -> None:
    window = provider.open_window(BufferSource.from_no_file("unique-test"))
    other = provider.open_window(BufferSource.from_no_file("other-test"))

    window.unique()

    assert window.valid
    assert not other.valid
    assert provider._windows == [window]


def test_unique_within_tabs_does_not_close_same_tab_windows(provider: PytoyWindowProviderDummy) -> None:
    window = provider.open_window(BufferSource.from_no_file("tab-unique-test"))
    other = provider.open_window(BufferSource.from_no_file("other-test"))

    window.unique(within_tabs=True, within_windows=False)

    assert window.valid
    assert other.valid


def test_deduplicate_rejects_invalid_scope(provider: PytoyWindowProviderDummy) -> None:
    window = provider.open_window(BufferSource.from_no_file("deduplicate-test"))

    with pytest.raises(ValueError, match="Invalid scope"):
        getattr(window, "deduplicate")("window")


def test_ensure_visible_uses_correct_value() -> None:
    assert ViewportMoveMode.ENSURE_VISIBLE.value == "ensure_visible"


def test_deduplicate_closes_windows_showing_the_same_buffer(provider: PytoyWindowProviderDummy) -> None:
    buffer = PytoyBufferDummy(BufferSource.from_no_file("shared-buffer"))
    window = provider._append_window(buffer)
    duplicate = provider._append_window(buffer)

    window.deduplicate()

    assert window.valid
    assert not duplicate.valid
    assert provider._windows == [window]
