from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, overload, Literal, Sequence

DefaultEnvironment = Literal["system"]
type EnvironmentKind = Literal["uv"] | DefaultEnvironment
# `naive` use `command` as is, `auto`, solves the apt evnrionment from `cwd`.
type ExecutionPreference =  Literal["auto"]  | EnvironmentKind 


class CommandWrapperProtocol(Protocol):
    @overload
    def __call__(self, arg: str) -> str: ...

    @overload
    def __call__(self, arg: list[str] | tuple[str]) -> list[str]: ...


type CommandWrapperType = CommandWrapperProtocol
type ExecutionWrapperType = CommandWrapperType | ExecutionPreference


class ToolRunnerStrategyProtocol(Protocol):
    kind: EnvironmentKind

    @overload
    def wrap(self, arg: str) -> str: ...
    
    @overload
    def wrap(self, arg: Sequence[str]) -> list[str]: ...

    def wrap(self, arg: str | Sequence[str]) -> str | list[str]: ...


class EnvironmentSolverProtocol(Protocol):
    @property
    def kind(self) -> EnvironmentKind: ...
    @property
    def installed(self) -> bool: ...
    def get_workspace(self, path: str | Path, /) -> Path | None : ...
    

class SystemEnvironmentSolver(EnvironmentSolverProtocol):
    
    @property
    def kind(self) -> EnvironmentKind:
        return "system"

    def installed(self) -> bool:
        return True 

    def get_workspace(self, path: str | Path, /) -> Path | None :
        path = Path(path)
        for parent in [path] + list(path.parents):
            if (parent / ".git").exists():
                return parent
        return None


@dataclass(frozen=True)
class SystemStrategy(ToolRunnerStrategyProtocol):
    kind: EnvironmentKind = "system"

    def wrap(self, arg: str | Sequence[str]):
        return arg
