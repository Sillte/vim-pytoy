from typing import Any, Protocol

from pytoy.shared.lib.event import Event


class ActionEvents(Protocol):
    """Semantic events emitted when a registered action is invoked."""

    def __getitem__(self, key: str) -> Event[Any]: ...

    def __delitem__(self, key: str) -> None: ...

    def clear(self) -> None: ...
