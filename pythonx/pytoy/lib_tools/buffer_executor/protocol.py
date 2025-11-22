from typing import Callable, Protocol, Any, Mapping, Self
from pathlib import Path

from pytoy.ui import PytoyBuffer


class BufferJobProtocol(Protocol):
    def __init__(
        self,
        name: str,
        stdout: PytoyBuffer | None = None,
        stderr: PytoyBuffer | None = None,
    ): ...
    
    @property
    def cwd(self) -> Path | str | None: 
        ...

    def job_start(
        self, command: str,
        on_start_callable: Callable[[], Mapping],
        on_closed_callable: Callable[[Self], Any],
        cwd: Path | str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None: ...

    @property
    def is_running(self) -> bool: ...

    def stop(self) -> None: ...

    @property
    def stdout(self) -> PytoyBuffer | None: ...

    @property
    def stderr(self) -> PytoyBuffer | None: ...
