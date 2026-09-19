from typing import Protocol

from pytoy.shared.ui.contract.quickfix.models import QuickfixRecord, QuickfixState


class QuickfixViewerProtocol(Protocol):
    def show(self) -> None: ...

    def close(self) -> None: ...

    def jump(self, *, with_focus: bool = False) -> QuickfixRecord | None: ...

    def sync_to_ui(self, only_index: bool = True) -> None: ...

    def sync_from_ui(self, only_index: bool = True) -> None: ...


__all__ = [
    "QuickfixViewerProtocol",
    "QuickfixRecord",
    "QuickfixState",
]
