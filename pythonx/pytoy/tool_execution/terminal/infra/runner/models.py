from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from pytoy.tool_execution.terminal.contract.models import TerminalDriverProtocol


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
    env: Mapping[str, str] | None = None
