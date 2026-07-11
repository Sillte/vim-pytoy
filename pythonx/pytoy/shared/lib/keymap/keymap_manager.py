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
            name = f"KeymapManagerEventBuffer{spec.buffer}_{key}_{suffix}"
        else:
            name = f"KeymapManagerEventGlobal_{key}_{suffix}"
        return name

    def register(self, spec: KeymapSpec) -> Keymap:
        if spec in self._keymaps:
            return self._keymaps[spec]
        name = self._generate_name(spec)
        emitter = EventEmitter()

        def on_event():
            emitter.fire(spec.buffer)

        registered_function = FunctionRegistry.register(on_event, name=name)
        command = self._make_register_command(registered_function, spec=spec)
        vim.command(command)
        keymap = Keymap(event=emitter.event, spec=spec, function=registered_function)

        self._keymaps[spec] = keymap
        self._emitters[spec] = emitter

        return keymap

    def deregister(self, spec: KeymapSpec) -> None:
        keymap = self._keymaps.pop(spec, None)
        if keymap is None:
            return
        vim.command(self._make_deregister_command(spec))
        FunctionRegistry.deregister(keymap.function)

    def _make_register_command(self, function: RegisteredFunction, spec: KeymapSpec) -> str:
        opts = []

        opts.append("<silent>")

        if spec.buffer is not None:
            opts.append(f"<buffer={spec.buffer}>")

        return f"nnoremap {' '.join(opts)} {spec.key} :call {function.impl_name}()<CR>"

    def _make_deregister_command(self, spec: KeymapSpec) -> str:
        if spec.buffer is None:
            return f"silent! nunmap {spec.key}"
        return f"silent! nunmap <buffer={spec.buffer}> {spec.key}"
