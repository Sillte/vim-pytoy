from typing import Callable, ClassVar
from pytoy.shared.command.core.models import CommandModel, RangeParam, CountParam
from pytoy.shared.command.app.protocol import CommandApplicationProtocol, GroupApplicationProtocol
from pytoy.shared.command.app.protocol import RangeSpec, CountSpec, NoneSpec, InvocationSpec


class CommandApplicationDummy(CommandApplicationProtocol):
    commands: ClassVar[dict[str, CommandModel]] = {}

    def command(self, name: str, *, invocation_spec: InvocationSpec | None = None, exists_ok: bool = True) -> Callable:
        def decorator(fn: Callable):
            command_model = CommandModel.from_callable(fn)
            self.commands[name] = command_model
            return fn

        return decorator
    
class DummySubCommandRegistry():
    def __init__(self, name: str) -> None:
        self._name = name
        self.sub_commands:  dict[str, CommandModel] = {}
        
    @property
    def name(self) -> str:
        return self._name
        
    def register(self, sub_command: str, fn: Callable):
        command_model = CommandModel.from_callable(fn)
        self.sub_commands[sub_command] = command_model
        
    def exists(self, sub_command: str):
        return sub_command in self.sub_commands

    def deregister(self, sub_command: str) -> None:
        self.sub_commands.pop(sub_command)


class CommandGroupDummy(GroupApplicationProtocol):
    groups: ClassVar[dict[str, DummySubCommandRegistry]] = {}

    def __init__(self, name: str, exists_ok: bool = True) -> None:
        self._name = name
        if (not exists_ok) and (self.name in CommandGroupDummy.groups):
            raise ValueError(f"`{self.name}` is already registered.")

        if name not in CommandGroupDummy.groups:
            CommandGroupDummy.groups[name] = DummySubCommandRegistry(name)

        self.group = CommandGroupDummy.groups[name]

    @property
    def name(self) -> str:
        return self._name

    def command(
        self,
        sub_command: str,
        *,
        invocation_spec: InvocationSpec | None = None,
        exists_ok: bool = True
    ) -> Callable:
        def decorator(fn: Callable) -> Callable:
            if not exists_ok and sub_command in self.group.sub_commands:
                raise ValueError(f"Command '{sub_command}' already exists in group '{self._name}'")
            self.group.register(sub_command, fn)
            return fn
        return decorator
