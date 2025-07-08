from typing import Protocol


class WindowsUtilProtocol(Protocol):
    """Protocol of windows util."""

    def sweep_windows(self) -> None:
        """Close the windows"""
        ...


    def create_window(self, bufname: str):
        """Creat a window from `bufname`."""
        ...
