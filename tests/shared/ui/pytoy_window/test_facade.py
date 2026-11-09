from pathlib import Path
from typing import Literal, Sequence

from pytoy.shared.lib.text import CharacterRange, CursorPosition
from pytoy.shared.ui.contract.window import PytoyWindowProtocol, PytoyWindowProviderProtocol
from pytoy.shared.ui.pytoy_buffer import BufferSource, PytoyBuffer
from pytoy.shared.ui.pytoy_window import PytoyWindow, PytoyWindowProvider, WindowCreationParam
from pytoy.shared.ui.pytoy_window.impls.dummy import PytoyWindowDummy


class RecordingWindowProvider(PytoyWindowProviderProtocol):
    def __init__(self) -> None:
        self.window = PytoyWindowDummy(1)
        self.received_param: WindowCreationParam | Literal["in-place", "vertical", "horizontal"] | None = None
        self.received_source: str | Path | BufferSource | None = None

    def get_current(self) -> PytoyWindowProtocol:
        return self.window

    def get_windows(self, only_normal_buffers: bool = True) -> Sequence[PytoyWindowProtocol]:
        if only_normal_buffers:
            return [self.window] if self.window.buffer.is_normal_type else []
        return [self.window]

    def open_window(
        self,
        source: str | Path | BufferSource,
        param: WindowCreationParam | Literal["in-place", "vertical", "horizontal"] = "in-place",
    ) -> PytoyWindowProtocol:
        self.received_param = param
        self.received_source = source
        return self.window


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


def test_window_provider_normalizes_facade_anchor_for_backend() -> None:
    backend = RecordingWindowProvider()
    provider = PytoyWindowProvider(backend)
    anchor_impl = PytoyWindowDummy(2)
    anchor = PytoyWindow(anchor_impl)
    param = WindowCreationParam.for_split("vertical", anchor=anchor)

    opened = provider.open_window(BufferSource.from_no_file("anchor-test"), param)

    assert opened.impl is backend.window
    assert isinstance(backend.received_param, WindowCreationParam)
    assert backend.received_param is not param
    assert backend.received_param.anchor is anchor_impl
    assert param.anchor is anchor
