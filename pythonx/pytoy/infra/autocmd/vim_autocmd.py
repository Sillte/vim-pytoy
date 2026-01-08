from pytoy.infra.core.models.event import Disposable, Event, EventEmitter
import vim
from pytoy.infra.vim_function import PytoyVimFunctions, VimFunctionName
from typing import Callable, Any, Literal, assert_never, Sequence
from pytoy.infra.core.models import Listener, Listener

ArgumentSpec = Literal["count", "event", "abuf", "afile"]

from dataclasses import dataclass


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

