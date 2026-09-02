from pytoy.shared.lib.event.domain import Event
from pytoy.shared.ui.contract.buffer import (
    BufferProtocol,
    BufferProviderProtocol,
    RangeOperatorProtocol,
)
from pytoy.shared.ui.pytoy_buffer.models import BufferID

PytoyBufferProtocol = BufferProtocol
PytoyBufferProviderProtocol = BufferProviderProtocol

__all__ = [
    "BufferProtocol",
    "BufferProviderProtocol",
    "BufferID",
    "Event",
    "PytoyBufferProtocol",
    "PytoyBufferProviderProtocol",
    "RangeOperatorProtocol",
]
