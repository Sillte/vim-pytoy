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
    """
    Here, the termiology of `uv` is borrowed. 
    * Project: it is also called as a package. It relates to one module.   
    * Workspace: The root folder of multiple projects.
    """
    @property
    def kind(self) -> EnvironmentKind: ...
    @property
    def installed(self) -> bool: ...
    def find_workspace(self, path: str | Path, /) -> Path | None : ...
    def find_project(self, path: str | Path, / ) -> Path | None : ...

    

class SystemEnvironmentSolver(EnvironmentSolverProtocol):
    @property
    def kind(self) -> EnvironmentKind:
        return "system"

    def installed(self) -> bool:
        return True 

    def find_workspace(self, path: str | Path, /) -> Path | None :
        path = Path(path)
        for parent in [path] + list(path.parents):
            if (parent / ".git").exists():
                return parent
        return None
    
    def find_project(self, path: str | Path, /) -> Path | None: 
        return self.find_workspace(path)



@dataclass(frozen=True)
class SystemStrategy(ToolRunnerStrategyProtocol):
    kind: EnvironmentKind = "system"

    def wrap(self, arg: str | Sequence[str]):
        return arg
