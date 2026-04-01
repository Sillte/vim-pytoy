from typing import Literal, Protocol, Callable
from dataclasses import dataclass
from textwrap import dedent
from pytoy.shared.lib.backend import get_backend_enum, BackendEnum
from pytoy.shared.command.models import CommandModel, RangeParam, CountParam 
from pytoy.shared.command.executor import CommandExecutor
from pytoy.shared.command.completion import CompletionService, CompletionParam, CompletionResult


# Currently, `InvocationSpec` seems not useful.
# If they are unnecessary, please delete them.
@dataclass(frozen=True)
class RangeSpec:
    default: tuple[int, int] | None = None
    type: Literal["Range"] = "Range"

@dataclass(frozen=True)
class CountSpec:
    default: int = 1
    type: Literal["Count"] = "Count"

@dataclass(frozen=True)
class NoneSpec:
    """No additional specification regarding invocation.
    """
    type: Literal["None"] = "None"

type InvocationSpec = RangeSpec | CountSpec | NoneSpec


class CommandApplicationProtocol(Protocol):
    def command(self,
                name: str,
                *,
                invocation_spec: InvocationSpec | None = None,
                exists_ok: bool = True) -> Callable: ...


def get_impl() -> CommandApplicationProtocol:
    backend_enum = get_backend_enum()
    if backend_enum in {BackendEnum.VIM, BackendEnum.NVIM, BackendEnum.VSCODE}:
        return CommandApplicationVim()
    else:
        return CommandApplicationDummy()


class CommandApplication:
    def __init__(self, impl: CommandApplicationProtocol | None = None) -> None:
        impl = impl or get_impl()
        self._impl = impl

    @property
    def impl(self) -> CommandApplicationProtocol:
        return self._impl

    def command(self, name: str, *, invocation_spec: InvocationSpec | None = None, exists_ok: bool = True) -> Callable:
        return self.impl.command(name, invocation_spec=invocation_spec, exists_ok=exists_ok)


class CommandApplicationDummy:
    def __init__(self):
        self._commands: dict[str, CommandModel] = {}

    def command(self, name: str, *, invocation_spec: InvocationSpec | None = None, exists_ok: bool = True) -> Callable:
        def decorator(fn: Callable):
            command_model = CommandModel.from_callable(fn)
            self._commands[name] = command_model
            return fn

        return decorator

class CommandApplicationVim:
    def __init__(self):
        pass

    def command(self, name:str, *, invocation_spec: InvocationSpec | None = None, exists_ok: bool = True) -> Callable:
        # [TODO]: Sophisticated name check is required.
        name = name[0].upper() + name[1:]
        def decorator(fn: Callable):
            VimAdapter.register_command(name=name, fn=fn)
            return fn
        return decorator



class VimAdapter:
    COMMAND_MAPS: dict[str, CommandModel] = dict()

    @classmethod
    def get_class_uri(cls):
        try:
            if __name__ != "__main__":
                prefix = f"{__name__}."
            else:
                prefix = ""
        except Exception:
            prefix = ""
        return f"{prefix}VimAdapter"

    @classmethod
    def execute(cls, name: str, line1: int , line2: int, count: int | None, args: str):
        if count == 0: 
            count = None

        command_model = cls.COMMAND_MAPS[name]
        executor = CommandExecutor()

        line1, line2 = sorted([line1, line2], reverse=False)
        range_param = RangeParam(line1 - 1, line2)  # 0-based, exclusive.
        injected_params = []
        injected_params.append(range_param)
        if count is not None:
            injected_params.append(CountParam(count=count))
        return executor.execute(command_model, command_line=args, injected_params=injected_params)

    @classmethod
    def complete(cls, name: str, leading: str, cmd_line:str, cursor_pos: int) -> list[str]:
        command_model = cls.COMMAND_MAPS[name]
        service = CompletionService()

        ind = cmd_line.find(name)
        if ind == -1:
            return []
        start = ind + len(name)
        line = cmd_line[start: ]
        offset = start
        cursor_pos = cursor_pos - offset

        param = CompletionParam(cmd_line=line, offset=offset, cursor_pos=cursor_pos)
        result = service.make_completions(command_model, param)
        values = [cand.value for cand in result.candidates]
        return values


    @classmethod
    def register_command(cls, name: str, fn: Callable):
        command_model = CommandModel.from_callable(fn)
        import vim

        cls.COMMAND_MAPS[name] = command_model
                                    
        func_name = f"Pytoy_Impl_{id(fn)}_{name}"
        complete_func_name = f"Pytoy_Complete_{id(fn)}_{name}"

        impl_procedure = f"""
#import {cls.get_class_uri()}
{cls.get_class_uri()}.execute(
"{name}",
int(vim.eval("a:line1")),
int(vim.eval("a:line2")),
int(vim.eval("a:count")),
vim.eval("a:q_args"),
        )
        """.strip()

        vim.command(dedent(f"""
        function! {func_name}(line1, line2, count, q_args)
python3 << EOF
{impl_procedure}
EOF
        endfunction
        """.strip()))


        quotated_name = f'"{name}"'
        #vim.command(rf"""
        #function! {complete_func_name}(arglead, cmdline, cursorpos)
        #    return py3eval("{cls.get_class_uri()}.complete(" . '{quotated_name}' . "," . string(a:arglead) . "," . string(a:cmdline) . "," . a:cursorpos . ")")
        #endfunction
        #""")

        vim.command(rf"""
        function! {complete_func_name}(arglead, cmdline, cursorpos)
            return py3eval("{cls.get_class_uri()}.complete(" . '{quotated_name}' . "," . json_encode(a:arglead) . "," . json_encode(a:cmdline) . "," . a:cursorpos . ")")
        endfunction
        """)


        vim.command(f"""
        command! -range -nargs=* -complete=customlist,{complete_func_name} {name} call {func_name}(<line1>, <line2>, <count>, <q-args>)
        """.strip())




"""
class CommandGroup:
    def __init__(self, name: str):
        self.name = name
        self.subcommands: Dict[str, CommandModel] = {}
        self.model = CommandModel(
            name=name,
            subcommands=self.subcommands,
        )

    def command(self, name: str) -> Callable:
        def decorator(fn: Callable):
            model = build_command_model(name, fn)
            self.subcommands[name] = model
            return fn
        return decorator
"""

if __name__ == "__main__":
    from typing import Literal 
    app = CommandApplication()
    @app.command("Test34343")
    def func(arg: Literal["AAA", "BBB"]):
        print(arg)
        ...
