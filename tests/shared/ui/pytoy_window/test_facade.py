from pytoy.shared.lib.text import CharacterRange, CursorPosition
from pytoy.shared.ui.pytoy_buffer import BufferSource, PytoyBuffer
from pytoy.shared.ui.pytoy_window import PytoyWindow, PytoyWindowProvider


def test_window_facade_uses_product_selected_backend() -> None:
    window = PytoyWindow.get_current()

    assert window.valid
    assert isinstance(window.buffer, PytoyBuffer)
    assert window.buffer.valid
    assert window.is_left()
    assert window.focus()


def test_window_exposes_buffer_and_cursor_operations() -> None:
    window = PytoyWindow.open(BufferSource.from_no_file("window-test"))
    window.buffer.init_buffer("first\nsecond")

    window.move_cursor(CursorPosition(1, 2))

    assert window.buffer.content == "first\nsecond"
    assert window.cursor == CursorPosition(1, 2)
    assert window.selection == CharacterRange(CursorPosition(0, 0), CursorPosition(1, 6))
    assert window.selected_line_range.start == 0
    assert window.selected_line_range.end == 2


def test_window_provider_returns_opened_window() -> None:
    provider = PytoyWindowProvider()
    window = provider.open_window(BufferSource.from_no_file("provider-window-test"))

    windows = provider.get_windows()

    assert any(item == window for item in windows)
    assert provider.get_current().valid
