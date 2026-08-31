from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pytoy.shared.lib.event.domain import Event
from pytoy.tool_execution.terminal.contract.models import TerminalDriverProtocol


@dataclass(frozen=True)
class JobEvents:
    on_job_exit: Event[Any]
    on_update: Event[int]


@dataclass
class ConsoleConfiguration:
    lines: int | None = None
    cols: int | None = None


@dataclass(frozen=True)
class TerminalJobRequest:
    driver: TerminalDriverProtocol
    name: str = "default"
    console: ConsoleConfiguration = field(default_factory=lambda: ConsoleConfiguration())


@dataclass(frozen=True)
class SpawnOption:
    cwd: str | Path | None = None
    env: dict[str, str] | None = None
