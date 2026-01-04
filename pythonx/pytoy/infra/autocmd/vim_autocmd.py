import vim
from pytoy.infra.vim_function import PytoyVimFunctions, VimFunctionName
from typing import Callable, Any, Literal, assert_never, Sequence

AutocmdArgument = Literal["count", "event", "abuf", "afile"]

class VimAutocmd:
    # For fallback `group` name.
    count_index: int = 0
    
    def __init__(
        self,
        event: str,
        *,
        pattern: str = "*",
        group: str | None = None,
        once: bool = False,
    ):
        self.event = event
        self.pattern = pattern
        self.once = once
        if not group:
            group = f"PytoyAutocmd_{event}_{self.count_index}"
            self.count_index += 1
        self._group: str = group

        # If this is not None, it means registered.
        self._vim_funcname: VimFunctionName | None = None

    def __eq__(self, other: object) -> bool:
        if other and isinstance(other, VimAutocmd):
            return (self.event == other.event and 
                    self.pattern == other.pattern and
                    self.group == other.group and 
                    self.once == other.once)
        return False

    @property
    def group(self) -> str:
        return self._group

    @property
    def funcname(self) -> VimFunctionName | None:
        return self._vim_funcname

    def _verify_function(self, fn: Callable[[Any], None], arguments: Sequence[AutocmdArgument]) -> None:
        import inspect

        sig = inspect.signature(fn)
        params = [
            p for p in sig.parameters.values() 
            if p.kind in (p.POSITIONAL_OR_KEYWORD, p.POSITIONAL_ONLY)
        ]
        for p in params:
            if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                raise TypeError(
                    f"Pytoy Autocmd error: Variadic arguments (*args or **kwargs) are not allowed in '{fn.__name__}'. "
                    f"Please define explicit arguments to match the autocmd specification."
                )
        if len(params) != len(arguments):
            raise TypeError(
                f"Argument mismatch for {fn.__name__}: "
                f"Vim Autocmd defines {len(arguments)} arguments ({arguments}), "
                f"but Python function expects {len(params)} arguments."
            )
        if any(p.default is not p.empty for p in params):
            raise TypeError(
                f"Pytoy Autocmd Strict Error: Default arguments are forbidden in '{fn.__name__}'. "
                f"Every argument must be explicit to match the Vim autocmd call."
            )

 
    def register(self, fn: Callable[[Any], None], arguments: Sequence[AutocmdArgument] | None = None) -> VimFunctionName:
        def _to_arg_str(argument: AutocmdArgument) -> str:
            match argument:
                case "count": return "v:count"
                case "event": return "v:event"
                case "abuf": return "expand('<abuf>')"
                case "afile": return "expand('<afile>')"
                case _:
                    assert_never(argument)

        if arguments is None: 
            arguments = []
        assert arguments is not None
        self._verify_function(fn, arguments)
        if self._vim_funcname:
            if self._vim_funcname == PytoyVimFunctions.to_vimfuncname(fn):
                print(f"Already the same function name is registered `{self.funcname=}`")
                return self._vim_funcname
            else:
                raise ValueError("The register is invoked twice with different function.")

        self._vim_funcname = PytoyVimFunctions.register(fn)

        arg_strs = [_to_arg_str(arg) for arg in arguments]
        arg_list_str = ",".join(arg_strs)
    
        once_flag = "++once" if self.once else ""

        full_command = (
            f"augroup {self.group} | "
            "autocmd! | "
            f"autocmd {self.event} {self.pattern} {once_flag} call {self._vim_funcname}({arg_list_str}) | "
            "augroup END"
        )
        try:
            vim.command(full_command)
        except vim.error as e:
            print(f"Vim Error: {e}", flush=True)
            print(f"Command: {full_command}", flush=True)
            raise
        return self._vim_funcname

    def deregister(self):
        vim.command(f"augroup {self.group} | autocmd! | augroup END")
        if self._vim_funcname is not None:
            PytoyVimFunctions.deregister(self._vim_funcname)
            self._vim_funcname = None


