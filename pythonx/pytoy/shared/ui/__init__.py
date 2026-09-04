"""Public API for the shared UI package."""

from pytoy.shared.ui.pytoy_buffer import BufferSource, PytoyBuffer, PytoyBufferProvider, make_buffer, make_duo_buffers
from pytoy.shared.ui.pytoy_quickfix import PytoyQuickfix, QuickfixRecord, handle_records
from pytoy.shared.ui.pytoy_window import PytoyWindow

__all__ = [
    "BufferSource",
    "PytoyBuffer",
    "PytoyBufferProvider",
    "PytoyQuickfix",
    "PytoyWindow",
    "QuickfixRecord",
    "handle_records",
    "make_buffer",
    "make_duo_buffers",
]
