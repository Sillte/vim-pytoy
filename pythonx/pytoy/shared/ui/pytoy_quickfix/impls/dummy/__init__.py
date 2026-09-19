from pytoy.shared.ui.contract.quickfix import (
    QuickfixRecord,
    QuickfixViewerProtocol,
)
from pytoy.shared.ui.pytoy_quickfix.entity import QuickfixEntity


class QuickfixDummyViewer(QuickfixViewerProtocol):
    def __init__(self, entity: QuickfixEntity) -> None:
        self._entity = entity

    def show(self) -> None:
        pass

    def close(self) -> None:
        pass

    def jump(self, *, with_focus: bool = False) -> QuickfixRecord | None:
        return self._entity.current_record

    def sync_to_ui(self, only_index: bool = True) -> None:
        pass

    def sync_from_ui(self, only_index: bool = True) -> None:
        pass
