from typing import Callable, ClassVar, Sequence, Any
from collections import defaultdict
from pytoy.shared.command.core.models import CommandModel, RangeParam, CountParam
from pytoy.shared.command.app.protocol import CommandApplicationProtocol, GroupApplicationProtocol
from pytoy.shared.command.app.protocol import RangeSpec, CountSpec, NoneSpec, InvocationSpec
from pytoy.shared.command.service import ExecutionService, CompletionService, CompletionParam, CompletionResult, CompletionCandidate


class DummyRegistry:
    commands: ClassVar[dict[str, CommandModel]] = {}
    groups: ClassVar[dict[str, dict[str, CommandModel]]] = defaultdict(dict)

    @classmethod
    def register_command(cls, name: str, command_model: CommandModel) -> None:
        cls.commands[name] = command_model

    @classmethod
    def register_group(cls, group_name: str, sub_command: str, command_model: CommandModel) -> None:
        cls.groups[group_name][sub_command] = command_model

    
    @classmethod
    def is_registered(cls, command_name: str) -> bool:
        return (command_name in cls.commands) or (command_name in cls.groups)

    @classmethod
    def is_registered_group(cls, command_name: str, sub_command: str) -> bool:
        group = cls.get_group(command_name)
        return (sub_command in group)
    
    @classmethod
    def get_command(cls, command: str) -> CommandModel:
        return cls.commands[command] 

    @classmethod
    def get_group(cls, group: str) -> dict[str, CommandModel]:
        if group not in cls.groups:
            raise ValueError(f"`{group=}` does not exists.")
        return cls.groups[group] 


class ExecutionDummy:
    
    @classmethod
    def execute_command(cls, command_name: str, cmd_line: str, injected_params: Sequence) -> Any:
        command_model = DummyRegistry.get_command(command_name)
        return ExecutionService().execute(command_model, cmd_line, injected_params)

    @classmethod
    def execute_group(cls, group_name: str, sub_command: str, cmd_line: str, injected_params: Sequence) -> Any:
        group = DummyRegistry.get_group(group_name)
        if (command_model := group.get(sub_command)):
            return ExecutionService().execute(command_model, cmd_line, injected_params)
        else:
            raise ValueError(f"`{sub_command=}` does not exist in `{group_name=}`")


class CompletionDummy:
    
    @classmethod
    def complete_command(cls, command_name: str, cmd_line: str, cursor_pos: int, offset: int=0) -> CompletionResult:
        command_model = DummyRegistry.get_command(command_name)
        param = CompletionParam(cmd_line=cmd_line, cursor_pos=cursor_pos, offset=offset)
        return CompletionService().make_completions(command_model, param)

    @classmethod
    def _get_strip_offset(cls, cmd_line: str, target: str) -> int:
        """Return the stripped `offset`.
        """
        stripped = cmd_line.lstrip()
        if not stripped.startswith(target):
            return 0
        leading_spaces = len(cmd_line) - len(stripped)
        return leading_spaces + len(target)

    @classmethod
    def complete_group(cls, group_name: str, cmd_line: str, cursor_pos: int, offset: int=0) -> CompletionResult:
        group = DummyRegistry.get_group(group_name)
        parts = cmd_line.split(" ", 1)
        sub_command = parts[0] if 1 < len(parts) else ""

        if (command_model := group.get(sub_command)):
            local_offset = cls._get_strip_offset(cmd_line, sub_command)
            cmd_line, cursor_pos, offset = cmd_line[local_offset:], cursor_pos - local_offset, offset + local_offset
            param = CompletionParam(cmd_line=cmd_line, cursor_pos=cursor_pos, offset=offset)
            return CompletionService().make_completions(command_model, param)
        else:
            cand_values = [key for key in group.keys() if key.startswith(sub_command)]
            cand_values = cand_values or list(group.keys())
            candidates = [CompletionCandidate(start=offset, end=offset+len(cand), value=cand) for cand in cand_values]
            return CompletionResult(candidates=candidates)


class CommandApplicationDummy(CommandApplicationProtocol):
    def command(self, name: str, *, invocation_spec: InvocationSpec | None = None, exists_ok: bool = True) -> Callable:
        def decorator(fn: Callable):
            command_model = CommandModel.from_callable(fn)
            DummyRegistry.register_command(name, command_model)
            return fn

        return decorator
    
class CommandGroupDummy(GroupApplicationProtocol):

    def __init__(self, name: str, exists_ok: bool = True) -> None:
        self._name = name
        if (not exists_ok) and DummyRegistry.is_registered(self.name):
            raise ValueError(f"`{self.name}` is already registered.")

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
            if (not exists_ok) and (DummyRegistry.is_registered_group(self.name, sub_command)):
                raise ValueError(f"Command '{sub_command}' already exists in group '{self.name}'")
            command_model = CommandModel.from_callable(fn)
            DummyRegistry.register_group(self.name, sub_command, command_model)
            return fn
        return decorator
