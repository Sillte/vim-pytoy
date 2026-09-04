from typing import Protocol, Sequence

from pytoy.shared.ui.contract.status_line.models import StatusLineItem


class StatusLineManagerProtocol(Protocol):
    def register(self, item: StatusLineItem) -> StatusLineItem: ...

    def deregister(self, item: StatusLineItem, strict_error: bool = False) -> bool: ...

    @property
    def items(self) -> Sequence[StatusLineItem]: ...


__all__ = ["StatusLineItem", "StatusLineManagerProtocol"]
