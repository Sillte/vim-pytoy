from typing import Callable, Protocol

from pytoy.ui import PytoyBuffer


class BufferJobProtocol(Protocol):
    def __init__(
        self,
        name: str,
        stdout: PytoyBuffer | None = None,
        stderr: PytoyBuffer | None = None,
        *,
        env=None,
        cwd=None,
    ):
        ...

    def job_start(
        self, command: str, on_start_callable: Callable, on_closed_callable: Callable
    ) -> None:
        ...

    @property
    def is_running(self) -> bool:
        ...

    def stop(self) -> None:
        ...


