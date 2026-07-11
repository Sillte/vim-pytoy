# Note:
# Here, I would like to use implenetation of `vim`
from dataclasses import dataclass
from pytoy.shared.lib.function.domain import RegisteredFunction
from pytoy.shared.lib.event import Event, EventEmitter


class KeySequence(str):
    pass


class Keys:
    ENTER = KeySequence("<CR>")
    ESC = KeySequence("<Esc>")
    TAB = KeySequence("<Tab>")


@dataclass(frozen=True)
class KeymapSpec:
    key: KeySequence
    buffer: int | None = None


@dataclass(frozen=True)
class Keymap:
    spec: KeymapSpec
    event: Event
    function: RegisteredFunction  # For debug.

    @property
    def key(self) -> KeySequence:
        return self.spec.key

    @property
    def buffer(self) -> int | None:
        return self.spec.buffer
