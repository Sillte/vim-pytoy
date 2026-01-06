from pytoy.infra.autocmd.vim_autocmd import VimAutocmdOld, Group, EmitSpec, VimAutocmd, ArgumentSpecs, ArgumentSpec, PayloadMapper
from pytoy.infra.vim_function import VimFunctionName, PytoyVimFunctions
from typing import Any, Callable


class AutoCmdManager:
    def __init__(self) -> None:
        self._dispatcher_vimname: VimFunctionName = PytoyVimFunctions.register(self._dispatcher)

        self._autocmds: dict[Group, VimAutocmd] = {}
        self._owners: dict[Group, object] = {}
        self._dispatched_functions: dict[Group, Callable] = {}

    def _dispatcher(self, group: Group, *args) -> None:
        func = self._dispatched_functions.get(group)
        if not func:
            return
        func(args)

    def register(self, group: Group, emitter_spec: EmitSpec, payload_mapper: PayloadMapper, owner: object | None = None) -> VimAutocmd:
        if group in self._autocmds:
            autocmd = self._autocmds[group]
            if autocmd.event_spec != emitter_spec or  autocmd.payload_mapper != payload_mapper:
                raise ValueError("Already `group` is registered, but `emitter_spec` or `argument_specs` are diffrent.")
            if owner != self._owners[group]:
                raise ValueError("The owner of group is different. ")
            return autocmd
        cmd = self._create_autocmd(group, emitter_spec, payload_mapper, owner)
        return cmd
        
        
    def _create_autocmd(self, group: Group, emitter_spec: EmitSpec, payload_mapper: PayloadMapper, owner: object | None) -> VimAutocmd:
        import vim
        cmd = VimAutocmd(group, emitter_spec, payload_mapper)
        command = cmd.make_command(self._dispatcher_vimname)
        vim.command(command)
        self._autocmds[cmd.group] = cmd
        self._owners[cmd.group] = owner
        self._dispatched_functions[cmd.group] = cmd.emitter.fire
        return cmd
        
    def deregister(self, group: Group) -> None: 
        import vim
        self._owners.pop(group)
        self._autocmds.pop(group)
        self._dispatched_functions.pop(group)
        vim.command(f"augroup {group} | autocmd! | augroup END")


    def deregister_all(self):
        for group in list(self._autocmds):
            self.deregister(group)

    def dispose_owner(self, owner: object):
        groups = [k for k, o in self._owners.items() if o is owner]
        for group in groups:
            self.deregister(group)

class AutocmdManagerProvider:
    def __init__(self):
        self._manager: AutoCmdManager | None = None

    def get(self) -> AutoCmdManager:
        if self._manager is None:
            self._manager = AutoCmdManager()
        return self._manager

    def dispose(self) -> None:
        if self._manager:
            self._manager.deregister_all()
            self._manager = None
_provider = AutocmdManagerProvider()

def get_autocmd_manager() -> AutoCmdManager: 
    return _provider.get()



class OldAutocmdManager:
    def __init__(self):
        self._autocmds: dict[Group, VimAutocmdOld] = {}
        self._owners: dict[Group, object] = {}

    def create_or_get_autocmd(self, event: str, group: str, once: bool, *, pattern="*", owner: object | None = None) -> VimAutocmdOld:
        if group in self._autocmds:
            autocmd = self._autocmds[group]
            r_owner = self._owners.get(group)
            if autocmd.event == event and autocmd.once == once and autocmd.pattern == pattern and r_owner == owner:
                return autocmd
            else:
                raise ValueError("Double creation of  Autocmd with inconsistency argument.")
            
        autocmd = VimAutocmdOld(event=event, group=group, once=once, pattern=pattern)
        self._autocmds[group] = autocmd
        if owner is not None:
            self._owners[group] = owner
        return autocmd  # or raise

    def delete_autocmd(self, group: Group) -> None:
        if group not in self._autocmds:
            return
        autocmd = self._autocmds.pop(group)
        autocmd.deregister()
        self._owners.pop(group, None)

    def dispose_owner(self, owner: object):
        groups = [k for k, o in self._owners.items() if o is owner]
        for group in groups:
            self.delete_autocmd(group)

    def clear_all(self):
        for group in list(self._autocmds):
            self.delete_autocmd(group)

_instance = OldAutocmdManager()
def get_old_autocmd_manager() -> OldAutocmdManager:
    return _instance
