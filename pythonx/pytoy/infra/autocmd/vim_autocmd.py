import vim
from pytoy.infra.vim_function import PytoyVimFunctions, VimFunctionName
from typing import Callable, Any, Literal, assert_never, Sequence
from pytoy.infra.core.models import Event, Listener, Disposable, EventEmitter, Listener, Disposable

ArgumentSpec = Literal["count", "event", "abuf", "afile"]

from dataclasses import dataclass, field


type Group = str

@dataclass(frozen=True)
class EmitSpec:
    event: str  # In reality, this is Vim Event.  
    pattern: str = "*"
    once: bool = False

EmitterPayload = tuple[Any, ...]

@dataclass(frozen=True)
class PayloadMapper[T]:
    arguments: Sequence[ArgumentSpec]
    transform: Callable[[EmitterPayload], T]


ArgumentSpecs = Sequence[ArgumentSpec]
DispatcherFuncName = str


@dataclass
class VimAutocmd[T: Any]:
    group: str  # Entity ID
    event_spec: EmitSpec
    payload_mapper: PayloadMapper[T]


    def __post_init__(self) -> None:
        self._emitter = EventEmitter[EmitterPayload]()

    @property
    def emitter(self) -> EventEmitter[EmitterPayload]:
        return self._emitter

    @property
    def event(self) -> Event[T]:
        return self._emitter.event.map(self.payload_mapper.transform) # noqa:  # notype

    def _to_args_str(self) -> str: 
        """Return the arguments inside of the parentheses.
        e.g.: {FunctionName}({Return})
        """
        def _to_arg_str(argument: ArgumentSpec) -> str:
            match argument:
                case "count": return "v:count"
                case "event": return "v:event"
                case "abuf": return "expand('<abuf>')"
                case "afile": return "expand('<afile>')"
                case _:
                    assert_never(argument)
        arg_strs = [_to_arg_str(arg) for arg in self.payload_mapper.arguments]
        return ",".join(arg_strs)
    
    def make_command(self, dispatcher_funcname: DispatcherFuncName) -> str:
        """Return the commands of `augroup`. 
        Note: `Dispatcher (Vim) Function`: The first argument is the group(Entity Id of Autocmd).
        After that, it takes the arbitrary number of arguments. 
        """
        emitter_spec = self.event_spec
        once_flag = "++once" if self.event_spec.once else ""
        arg_list_str = self._to_args_str()

        full_command = (
            f"augroup {self.group} | "
            "autocmd! | "
            f"autocmd {emitter_spec.event} {emitter_spec.pattern} {once_flag} call {dispatcher_funcname}('{self.group}', {arg_list_str}) | "
            "augroup END"
        )
        return full_command



class VimAutocmdOld:
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
        if other and isinstance(other, VimAutocmdOld):
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

    def _verify_function(self, fn: Callable[[Any], None], arguments: Sequence[ArgumentSpec]) -> None:
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

 
    def register(self, fn: Callable[[Any], None], arguments: Sequence[ArgumentSpec] | None = None) -> VimFunctionName:
        def _to_arg_str(argument: ArgumentSpec) -> str:
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
        from pytoy.infra.timertask import TimerTask
        def _inner():
            vim.command(f"augroup {self.group} | autocmd! | augroup END")
            if self._vim_funcname is not None:
                PytoyVimFunctions.deregister(self._vim_funcname)
                self._vim_funcname = None
        TimerTask.execute_oneshot(_inner, interval=0)


