from pytoy.infra.autocmd import VimAutocmd, AutocmdManager, get_autocmd_manager
from pytoy.infra.events.models import EventSourceProtocol, Event, EventEmitter

from typing import Callable


type WinClosedCallback = Callable[[int], None]

# AutocmdManager manages Vim autocmds which are global to the Vim process.
# Therefore, a single shared instance is used by default.

class WinClosedEventSource(EventSourceProtocol):
    def __init__(self, win_id: int, autocmd_manager: AutocmdManager | None = None) -> None:
        self._emitter = EventEmitter[int]()
        self._event = self._emitter.event
        self._emitted = False

        self.winid = win_id
        if autocmd_manager is None:
            autocmd_manager = get_autocmd_manager()
        
        group = f"pytoy_event_winclosed_{self.winid}"
        self.group = group
        self.autocmd_manager = autocmd_manager
        self.autocmd = autocmd_manager.create_or_get_autocmd(event="WinClosed", once=False, group=group)
        self.autocmd.register(self._on_autocmd, ["afile"])

    @property
    def event(self) -> Event:
        return self._event

    def _on_autocmd(self, afile: str):
        winid = int(afile)
        if winid != self.winid or self._emitted:
            return 

        self._emitter.fire(winid)
        self._emitted = True
        # This is called only once, so delete the autocmd. 
        self.autocmd_manager.delete_autocmd(self.group)

    @property
    def emitted(self) -> bool:
        return self._emitted
