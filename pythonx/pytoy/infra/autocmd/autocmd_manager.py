from pytoy.infra.autocmd.vim_autocmd import VimAutocmd

type Group = str

class AutocmdManager:
    def __init__(self):
        self._autocmds: dict[Group, VimAutocmd] = {}
        self._owners: dict[Group, object] = {}

    def create_or_get_autocmd(self, event: str, group: str, once: bool, *, pattern="*", owner: object | None = None) -> VimAutocmd:
        if group in self._autocmds:
            autocmd = self._autocmds[group]
            r_owner = self._owners.get(group)
            if autocmd.event == event and autocmd.once == once and autocmd.pattern == pattern and r_owner == owner:
                return autocmd
            else:
                raise ValueError("Double creation of  Autocmd with inconsistency argument.")
            
        autocmd = VimAutocmd(event=event, group=group, once=once, pattern=pattern)
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

_instance = AutocmdManager()
def get_autocmd_manager() -> AutocmdManager:
    return _instance
