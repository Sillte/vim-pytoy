from dataclasses import dataclass
from typing import Callable, Any, Literal, assert_never
from textwrap import dedent
from pytoy.shared.lib.backend import get_backend_enum, BackendEnum
from pytoy.shared.command.core.models import CommandModel, RangeParam, CountParam
from pytoy.shared.command.service.executor import ExecutionService
from pytoy.shared.command.service.completion import CompletionService, CompletionParam, CompletionResult
from pytoy.shared.command.app.protocol import CommandApplicationProtocol, GroupApplicationProtocol
from pytoy.shared.command.app.protocol import RangeSpec, CountSpec, NoneSpec, InvocationSpec

import re

_pattern = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
def normalize_vim_command_name(name: str) -> str:
    if not _pattern.match(name):
        raise ValueError(f"Invalid command name `{name}`. ")
    return name[0].upper() + name[1:]

def normalize_sub_command(sub_command: str) -> str:
    if not _pattern.match(sub_command):
        raise ValueError(f"Invalid subcommand `{sub_command}`")
    return sub_command


class GroupApplicationVim(GroupApplicationProtocol):
    def __init__(self, name: str, exist_ok: bool = True):
        self._name = normalize_vim_command_name(name)
        if (not exist_ok) and VimCommandAdapter.is_registered(self.name):
            raise ValueError(f"`{self.name}` is already registered.")

    @property
    def name(self) -> str:
        return self._name

    def command(
        self, sub_command: str, *, invocation_spec: InvocationSpec | None = None, exists_ok: bool = True
    ) -> Callable:
        sub_command = normalize_sub_command(sub_command)
        if (not exists_ok) and VimCommandAdapter.is_registered_subcommand(self.name, sub_command):
            raise ValueError(f"Subcommand:`{sub_command}` of `{self.name}`is already registered.")
        def decorator(fn: Callable):
            VimCommandAdapter.register_group(group_name=self.name, sub_command=sub_command, fn=fn)
            return fn
        return decorator


class CommandApplicationVim(CommandApplicationProtocol):
    def command(self, name: str, *, invocation_spec: InvocationSpec | None = None, exists_ok: bool = True) -> Callable:
        name = normalize_vim_command_name(name)
        if (not exists_ok) and VimCommandAdapter.is_registered(name):
            raise ValueError(f"Command `{name}` is already registered.")

        def decorator(fn: Callable):
            VimCommandAdapter.register_command(name=name, fn=fn)
            return fn
        return decorator


def execute_command(command_model: CommandModel, line1: int, line2: int, count: int | None, cmd_line: str) -> Any:
    """Execute `command` based on `Command` model."""
    executor = ExecutionService()
    if count == 0:
        count = None

    line1, line2 = sorted([line1, line2], reverse=False)
    range_param = RangeParam(line1 - 1, line2)  # 0-based, exclusive.
    injected_params = []
    injected_params.append(range_param)
    if count is not None:
        injected_params.append(CountParam(count=count))
    return executor.execute(command_model, command_line=cmd_line, injected_params=injected_params)


def complete_command(command_model: CommandModel, input_line: str, cursor_pos: int, offset: int) -> list[str]:
    """Make a completion of CommandModel.
    `input_line`: It handles the `cmd` line which is regarded as the input of `CommandModel`.
    `cursor_pos`: the cursor position within `input_line`.
    `offset`: the offset of the `cursor`. Typically, it is affected  by stripping the prefix of user inputs.
    """
    service = CompletionService()
    param = CompletionParam(cmd_line=input_line, offset=offset, cursor_pos=cursor_pos)
    result = service.make_completions(command_model, param)
    values = [cand.value for cand in result.candidates]
    return values


class VimCommandAdapter:
    COMMAND_MAPS: dict[str, CommandModel] = dict()
    GROUP_MAPS: dict[str, dict[str, CommandModel]] = dict()

    @classmethod
    def get_class_uri(cls):
        try:
            if __name__ != "__main__":
                prefix = f"{__name__}."
            else:
                prefix = ""
        except Exception:
            prefix = ""
        return f"{prefix}VimCommandAdapter"

    @classmethod
    def execute_command(cls, name: str, line1: int, line2: int, count: int | None, cmd_line: str):
        command_model = cls.COMMAND_MAPS[name]
        return execute_command(command_model, line1, line2, count, cmd_line)

    @classmethod
    def execute_group(cls, name: str, line1: int, line2: int, count: int | None, cmd_line: str):
        group = cls.GROUP_MAPS[name]
        parts = cmd_line.strip().split(" ", 1)
        sub_command = parts[0] if parts else ""
        rest = parts[1] if len(parts) > 1 else ""
        if not sub_command:
            raise ValueError(f"Sub-command is necessary. `{group.keys()}`")
        elif sub_command not in group:
            raise ValueError(f"Specified sub-command must belong to `{group.keys()}`")
        command_model = group[sub_command]
        return execute_command(command_model, line1, line2, count, rest)
    
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
    def complete_command(cls, name: str, leading: str, cmd_line: str, cursor_pos: int) -> list[str]:
        command_model = cls.COMMAND_MAPS[name]
        offset = cls._get_strip_offset(cmd_line, name)
        line, cursor_pos = cmd_line[offset:], cursor_pos - offset
        return complete_command(command_model, line, cursor_pos, offset=offset)

    @classmethod
    def complete_group(cls, name: str, leading: str, cmd_line: str, cursor_pos: int) -> list[str]:
        group = cls.GROUP_MAPS[name]

        command_offset = cls._get_strip_offset(cmd_line, name)
        cmd_line, cursor_pos, offset = cmd_line[command_offset:], cursor_pos - command_offset, command_offset

        parts = cmd_line.strip().split(" ", 1)
        sub_command = parts[0] if parts else ""
        rest = parts[1] if 1 < len(parts) else ""
        if sub_command in group and rest:
            command_model = group[sub_command]
            sub_offset = cls._get_strip_offset(cmd_line, sub_command)
            cmd_line, cursor_pos, offset = cmd_line[sub_offset:], cursor_pos - sub_offset, offset + sub_offset
            return complete_command(command_model, cmd_line, cursor_pos, offset)
        else:
            candidates = [cand for cand in group.keys() if cand.startswith(sub_command)]
            if candidates:
                return candidates
            else:
                return list(group.keys())
            
    @classmethod
    def is_registered(cls, name: str) -> bool:
        return (name in cls.COMMAND_MAPS) or (name in cls.GROUP_MAPS)

    @classmethod
    def is_registered_subcommand(cls, group_name: str, sub_command: str) -> bool:
        return (sub_command in cls.GROUP_MAPS.get(group_name, {}))

    @classmethod
    def register_command(cls, name: str, fn: Callable):
        command_model = CommandModel.from_callable(fn)
        cls.COMMAND_MAPS[name] = command_model

        func_name = f"Pytoy_Command_Impl_{id(fn)}_{name}"
        complete_func_name = f"Pytoy_Command_Complete_{id(fn)}_{name}"
        cls._register_vim_command(name, func_name, complete_func_name, kind="command")

    @classmethod
    def register_group(cls, group_name: str, sub_command: str, fn: Callable):
        if group_name not in cls.GROUP_MAPS:
            cls.GROUP_MAPS[group_name] = {}
            func_name = f"Pytoy_Group_Impl_{group_name}"
            complete_func_name = f"Pytoy_Group_Complete_{group_name}"
            cls._register_vim_command(group_name, func_name, complete_func_name, kind="group")

        group = cls.GROUP_MAPS[group_name]
        group[sub_command] = CommandModel.from_callable(fn)

    @classmethod
    def _register_vim_command(
        cls, name: str, func_name: str, complete_func_name: str, kind: Literal["command", "group"] = "command"
    ) -> None:
        """As a contract, when the `name` command is invoked, the `funcname` vim function is called,
        the classmethod (`execute_{kind}`) is called, depending of `kind`.
        The completer function name becomes `completer_name`.
        """
        import vim

        match kind:
            case "command":
                python_execute_function: str = f"{cls.get_class_uri()}.execute_{kind}"
                python_complete_function: str = f"{cls.get_class_uri()}.complete_{kind}"
            case "group":
                python_execute_function: str = f"{cls.get_class_uri()}.execute_{kind}"
                python_complete_function: str = f"{cls.get_class_uri()}.complete_{kind}"
            case _:
                assert_never(kind)

        impl_procedure = f"""
{python_execute_function}(
"{name}",
int(vim.eval("a:line1")),
int(vim.eval("a:line2")),
int(vim.eval("a:count")),
vim.eval("a:q_args"),
        )
        """.strip()

        vim.command(
            dedent(
                f"""
        function! {func_name}(line1, line2, count, q_args)
python3 << EOF
{impl_procedure}
EOF
        endfunction
        """.strip()
            )
        )

        quotated_name = f'"{name}"'
        vim.command(rf"""
        function! {complete_func_name}(arglead, cmdline, cursorpos)
            return py3eval("{python_complete_function}(" . '{quotated_name}' . "," . json_encode(a:arglead) . "," . json_encode(a:cmdline) . "," . a:cursorpos . ")")
        endfunction
        """)

        vim.command(
            f"""
        command! -range -nargs=* -complete=customlist,{complete_func_name} {name} call {func_name}(<line1>, <line2>, <count>, <q-args>)
        """.strip()
        )

if __name__ == "__main__":
    from pytoy.shared.command import App, Group

    group = Group("SampleGroup")
    @group.command("run")
    def func(arg: Literal["hoafeafae", "afafafa"]):
        print(arg)

    app = App()
    @app.command("SampleApp")
    def func2(arg: Literal["hoafeafae", "afafafa"]):
        print(arg)