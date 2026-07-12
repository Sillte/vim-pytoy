import vim
import re

from pytoy.shared.lib.function import FunctionRegistry
from pytoy.shared.lib.function.domain import RegisteredFunction
from pytoy.shared.lib.keymap.models import Keymap, KeymapSpec
from pytoy.shared.lib.event import EventEmitter


class KeymapManager:
    def __init__(self):
        self._keymaps: dict[KeymapSpec, Keymap] = {}
        self._emitters: dict[KeymapSpec, EventEmitter] = {}

    def _generate_name(self, spec: KeymapSpec) -> str:
        import hashlib

        suffix = hashlib.sha1(repr(spec).encode()).hexdigest()[:8]

        key = re.sub(r"[^0-9a-zA-Z_]", "_", str(spec.key))
        if spec.buffer is not None:
            return f"KeymapManagerEventBuffer{spec.buffer}_{key}_{suffix}"
        return f"KeymapManagerEventGlobal_{key}_{suffix}"

    def register(self, spec: KeymapSpec) -> Keymap:
        if spec in self._keymaps:
            return self._keymaps[spec]

        emitter = EventEmitter()

        def on_event():
            emitter.fire(spec.buffer)

        registered_function = FunctionRegistry.register(
            on_event,
            name=self._generate_name(spec),
        )

        command = self._make_register_command(registered_function, spec)
        self._execute_command(spec, command)

        keymap = Keymap(
            event=emitter.event,
            spec=spec,
            function=registered_function,
        )

        self._keymaps[spec] = keymap
        self._emitters[spec] = emitter
        return keymap

    def deregister(self, spec: KeymapSpec) -> None:
        keymap = self._keymaps.pop(spec, None)
        if keymap is None:
            return

        self._execute_command(spec, self._make_deregister_command(spec))
        self._emitters.pop(spec, None)
        FunctionRegistry.deregister(keymap.function)

    def _execute_command(self, spec: KeymapSpec, command: str) -> None:
        if spec.buffer is None:
            vim.command(command)
            return

        winid = int(vim.eval(f"bufwinid({spec.buffer})"))
        if winid == -1:
            raise ValueError(
                f"Buffer {spec.buffer} is not displayed in any window."
            )

        escaped = command.replace("'", "''")
        vim.command(f"call win_execute({winid}, '{escaped}')")

    def _make_register_command(
        self,
        function: RegisteredFunction,
        spec: KeymapSpec,
    ) -> str:
        opts = ["<silent>"]

        if spec.buffer is not None:
            opts.append("<buffer>")

        return (
            f"nnoremap {' '.join(opts)} "
            f"{spec.key} "
            f":call {function.impl_name}()<CR>"
        )

    def _make_deregister_command(self, spec: KeymapSpec) -> str:
        if spec.buffer is None:
            return f"silent! nunmap {spec.key}"

        return f"silent! nunmap <buffer> {spec.key}"