from pytoy.shared.ui.status_line.protocol import StatusLineManagerProtocol, StatusLineItem
from typing import List, Sequence

class StatusLineManagerDummy(StatusLineManagerProtocol):
    _instance: "StatusLineManagerDummy | None" = None

    def __init__(self):
        if StatusLineManagerDummy._instance is not None:
            return
        self._items: List[StatusLineItem] = []
        StatusLineManagerDummy._instance = self

    def register(self, item: StatusLineItem) -> StatusLineItem:
        self._items.append(item)
        return item

    def deregister(self, item: StatusLineItem, strict_error: bool = False) -> bool:
        if item not in self._items and strict_error:
            raise ValueError("Item not found in status line manager.")
        try:
            self._items.remove(item)
            return True
        except ValueError:
            return False

    @property
    def items(self) -> Sequence[StatusLineItem]:
        return self._items