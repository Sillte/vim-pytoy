from typing import Protocol, Sequence

from dataclasses import dataclass, replace
from typing import Self, Mapping, Sequence
from pytoy.ui.status_line.models import StatusLineItem


class StatusLineManagerProtocol(Protocol):
    """ It depends on the backend.
    * `StatusLineItem` is regarded as `ValueObject`. 
    * This must be called in the main thread,  
    """

    def register(self, item: StatusLineItem) -> StatusLineItem:
        ...

    def deregister(self, item: StatusLineItem, strict_error=False) -> bool:
        ...

    @property
    def items(self) -> Sequence[StatusLineItem]:
        ...
