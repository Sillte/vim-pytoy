from typing import Protocol


class WindowsUtilProtocol(Protocol):
    """Protocol of windows util."""

    def sweep_windows(self) -> None:
        """Close the windows"""
        ...

    def is_leftwindow(self, ) -> bool:
        """Return whether the current window is left or not."""
        ...

    def create_window(self, bufname: str):
        """Creat a window from `bufname`."""
        ...
