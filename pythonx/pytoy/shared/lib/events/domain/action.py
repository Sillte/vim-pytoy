from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from pytoy.shared.lib.event import Event


class ActionEvents(Protocol):
    """Semantic events emitted when a registered action is invoked."""

    def __getitem__(self, key: str) -> Event[Any]: ...

    def __delitem__(self, key: str) -> None: ...

    def clear(self) -> None: ...


class KeySequence(str):
    pass


class Keys:
    ENTER = KeySequence("<CR>")
    ESC = KeySequence("<Esc>")
    TAB = KeySequence("<Tab>")


@dataclass(frozen=True)
class KeymapSpec:
    key: KeySequence
    buffer: int | None = None


class KeyEventManagerImpl(Protocol):
    def register(self, spec: KeymapSpec) -> Event[int | None]: ...

    def deregister(self, spec: KeymapSpec) -> None: ...

    @property
    def specs(self) -> Sequence[KeymapSpec]: ...
