from pytoy.infra.autocmd.autocmd_manager import get_autocmd_manager, EmitSpec, PayloadMapper, AutoCmdManager

from pytoy.infra.core.models.event import Event
from pytoy.infra.events.entity_event import  GlobalEvent
from functools import cached_property


class GlobalWindowEventProvider:
    def __init__(self,  autocmd_manager: AutoCmdManager) -> None:
        self.manager = autocmd_manager 

    @cached_property
    def winclosed(self) -> GlobalEvent[int]:
        group = f"PytoyAnyWinClosedGroup_{id(self.manager)}"
        emit_spec = EmitSpec(event="WinClosed")
        payload_mapper = PayloadMapper(arguments=["afile"], transform=lambda args: int(args[0]))
        autocmd = self.manager.register(group, emit_spec, payload_mapper)
        return GlobalEvent(autocmd.event)

global_provider = GlobalWindowEventProvider(get_autocmd_manager())

class ScopedWindowEventProvider:
    global_provider: GlobalWindowEventProvider  = global_provider

    @classmethod
    def get_winclosed_event(cls, bufnr: int) -> Event[int]:
        winclosed = cls.global_provider.winclosed
        return winclosed.at(bufnr)
