import hashlib
import re
from dataclasses import dataclass

from pytoy.shared.lib.event import Event, EventEmitter
from pytoy.shared.lib.events.domain.action import KeymapSpec
from pytoy.shared.lib.function import FunctionRegistry, RegisteredFunction


@dataclass(frozen=True)
class Keymap:
    spec: KeymapSpec
    event: Event[int | None]
    function: RegisteredFunction


class VimKeyEventManager:
    def __init__(self) -> None:
        self._keymaps: dict[KeymapSpec, Keymap] = {}

    def _generate_name(self, spec: KeymapSpec) -> str:
        suffix = hashlib.sha1(repr(spec).encode()).hexdigest()[:8]
        key = re.sub(r"[^0-9a-zA-Z_]", "_", str(spec.key))
        if spec.buffer is not None:
            return f"KeyEventBuffer{spec.buffer}_{key}_{suffix}"
        return f"KeyEventGlobal_{key}_{suffix}"

    def register(self, spec: KeymapSpec) -> Event[int | None]:
        if spec in self._keymaps:
            return self._keymaps[spec].event

        emitter = EventEmitter[int | None]()

        def on_event() -> None:
            emitter.fire(spec.buffer)

        registered_function = FunctionRegistry.register(
            on_event,
            name=self._generate_name(spec),
        )
        self._execute_command(spec, self._make_register_command(registered_function, spec))

        keymap = Keymap(spec, emitter.event, registered_function)
        self._keymaps[spec] = keymap
        return keymap.event

    def deregister(self, spec: KeymapSpec) -> None:
        keymap = self._keymaps.pop(spec, None)
        if keymap is None:
            return

        self._execute_command(spec, self._make_deregister_command(spec))
        FunctionRegistry.deregister(keymap.function)

    @property
    def specs(self) -> tuple[KeymapSpec, ...]:
        return tuple(self._keymaps)

    def _execute_command(self, spec: KeymapSpec, command: str) -> None:
        import vim

        if spec.buffer is None:
            vim.command(command)
            return

        winid = int(vim.eval(f"bufwinid({spec.buffer})"))
        if winid == -1:
            raise ValueError(f"Buffer {spec.buffer} is not displayed in any window.")

        escaped = command.replace("'", "''")
        vim.command(f"call win_execute({winid}, '{escaped}')")

    def _make_register_command(self, function: RegisteredFunction, spec: KeymapSpec) -> str:
        opts = ["<silent>"]
        if spec.buffer is not None:
            opts.append("<buffer>")
        return f"nnoremap {' '.join(opts)} {spec.key} :call {function.impl_name}()<CR>"

    def _make_deregister_command(self, spec: KeymapSpec) -> str:
        if spec.buffer is None:
            return f"silent! nunmap {spec.key}"
        return f"silent! nunmap <buffer> {spec.key}"
