from pytoy.infra.autocmd.vim_autocmd import Group, EmitSpec, VimAutocmd,  PayloadMapper
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
        """Note that `PayloaderMappger.transform` (callable) is also regarded as the value for identity check.  
        In typical case, usage of lambda function should be avoided.
        """
        if group in self._autocmds:
            autocmd = self._autocmds[group]
            if autocmd.event_spec != emitter_spec or  autocmd.payload_mapper != payload_mapper:
                raise ValueError(f"Already `group` is registered, but `emitter_spec` or `argument_specs` are diffrent, {group=}, {emitter_spec=}, {autocmd.event_spec=}")
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


