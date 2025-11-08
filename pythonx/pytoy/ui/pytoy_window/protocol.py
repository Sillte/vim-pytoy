from typing import Protocol

from pytoy.ui.pytoy_buffer import PytoyBuffer


class PytoyWindowProtocol(Protocol):
    @property
    def buffer(self) -> PytoyBuffer: ...

    @property
    def valid(self) -> bool:
        """Return whether the window is valid or not"""
        ...

    def is_left(self) -> bool:
        """Return whether this is leftwindow or not."""
        ...

    def close(self) -> bool: ...

    def focus(self) -> bool: ...

    def __eq__(self, other: object) -> bool: ...

    def unique(self, within_tab: bool = False) -> None: ...


class PytoyWindowProviderProtocol(Protocol):
    def get_current(self) -> PytoyWindowProtocol: ...

    def get_windows(self) -> list[PytoyWindowProtocol]: ...

    def create_window(
        self,
        bufname: str,
        mode: str = "vertical",
        base_window: PytoyWindowProtocol | None = None,
    ) -> PytoyWindowProtocol: ...
