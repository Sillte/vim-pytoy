from pytoy.tool_execution.terminal.contract import (
    TerminalDriverProtocol,
)

DEFAULT_SHELL_DRIVER_NAME = "shell"


class TerminalDriverManager:
    def __init__(self):
        self._drivers: dict[str, type[TerminalDriverProtocol]] = {}

    def register(self, driver_kind: str):
        def _wrap[T: TerminalDriverProtocol](driver_class: type[T]) -> type[T]:
            self._drivers[driver_kind] = driver_class
            return driver_class

        return _wrap

    def _is_registered(self, driver_kind: str) -> bool:
        return driver_kind in self._drivers

    @property
    def kinds(self) -> list[str]:
        return list(self._drivers.keys())

    def create(self, driver_kind: str, **kwargs) -> TerminalDriverProtocol:
        cls = self._drivers.get(driver_kind)
        if not cls:
            raise ValueError(f"Driver {driver_kind} not found")
        return cls(**kwargs)
