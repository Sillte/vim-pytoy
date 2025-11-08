from pytoy.ui.pytoy_buffer.protocol import PytoyBufferProtocol, RangeSelectorProtocol
from pytoy.ui import get_ui_enum, UIEnum


class RangeSelector(RangeSelectorProtocol):
    """Return the `str` related to Buffer."""

    def __init__(self, impl: RangeSelectorProtocol):
        self._impl = impl

    @property
    def buffer(self) -> PytoyBufferProtocol:
        return self._impl.buffer

    def get_lines(self, line1: int, line2: int) -> list[str]:
        return self._impl.get_lines(line1, line2)

    def get_range(self, line1: int, pos1: int, line2: int, pos2: int) -> str:
        return self._impl.get_range(line1, pos1, line2, pos2)


def make_selector(impl_buffer: PytoyBufferProtocol):
    if get_ui_enum() == UIEnum.VSCODE:
        from pytoy.ui.pytoy_buffer.impl_vscode import (
            RangeSelectorVSCode,
            PytoyBufferVSCode,
        )

        assert isinstance(impl_buffer, PytoyBufferVSCode)
        impl = RangeSelectorVSCode(impl_buffer)
        return RangeSelector(impl)
    else:
        from pytoy.ui.pytoy_buffer.impl_vim import RangeSelectorVim, PytoyBufferVim

        assert isinstance(impl_buffer, PytoyBufferVim)
        impl = RangeSelectorVim(impl_buffer)
        return RangeSelector(impl)
