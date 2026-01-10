from .models import Sequence, InputOperation, ConsoleSnapshot, ConsoleConfigration, ConsoleConfigurationRequest
from .models import WaitOperation, ExecutorEvents
from typing import Protocol

class TTYApplicationProtocol(Protocol):
    @property
    def command(self) -> str:
        """The name of command"""
        ...

    def is_busy(self, children_pids: list[int], snapshot: ConsoleSnapshot) -> bool | None:
        """Return whether the `terminal` is busy or not.
        Note that sometimes, the estimation is not perfect. (very difficult to realize perfection).
        If the return is True, it is 100% sure that the process is busy,
        If the return is False, it cannot guarantee that the process is NOT working.
        (When we have to rely on the lastline, mis-detection cannot be avoided.)
        """
        ...

    def make_lines(self, input_str: str) -> Sequence[InputOperation]:
        """Make the lines which is sent into `pty`.

        * If `\r` / `\n` is added at the end of elements, they are sent as is.
        * Otherwise, the LF is appended at the end of elements.
        """
        ...

    def interrupt(self, pid: int, children_pids: list[int]) -> None:
        """Interrupt the process. if possible."""
        ...

class TTYApplicationExecutorProtocol(Protocol):

    def send(self, input: str | WaitOperation) -> None:
        ...

    @property
    def alive(self) -> bool:
        ...

    @property
    def busy(self) -> bool | None:
        ...

    def interrupt(self) ->  None:
        ...

    def terminate(self) -> None:
        """Requres idempotency.
        """
        ...

    @property
    def snapshot(self) -> ConsoleSnapshot:
        ...

    @property
    def pid(self) -> int:
        ...

    @property
    def children_pids(self) -> list[int]:
        ...

        
    @property
    def events(self) -> ExecutorEvents:
        ...


