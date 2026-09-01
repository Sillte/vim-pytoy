from dataclasses import dataclass
from pathlib import Path
from typing import Self, assert_never

from .models import (
    CommandWrapperType,
    EnvironmentKind,
    SystemStrategy,
    ToolRunnerStrategyProtocol,
)
from .uv_environment import UvStrategy


@dataclass(frozen=True)
class ToolRunnerStrategy:
    impl: ToolRunnerStrategyProtocol

    @property
    def kind(self) -> EnvironmentKind:
        return self.impl.kind

    @property
    def command_wrapper(self) -> CommandWrapperType:
        return self.impl.wrap

    @classmethod
    def from_kind(cls, environment_kind: EnvironmentKind) -> Self:
        match environment_kind:
            case "system":
                return cls(impl=SystemStrategy())
            case "uv":
                return cls(impl=UvStrategy())
            case _:
                assert_never(environment_kind)


@dataclass(frozen=True)
class ResolvedExecutionEnvironment:
    tool_runner_strategy: ToolRunnerStrategy
    workspace: Path | None
    base_path: Path

    @property
    def kind(self) -> EnvironmentKind:
        return self.tool_runner_strategy.kind

    @property
    def command_wrapper(self) -> CommandWrapperType:
        return self.tool_runner_strategy.command_wrapper
