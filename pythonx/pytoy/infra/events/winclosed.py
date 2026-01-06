from pytoy.infra.autocmd.autocmd_manager import get_autocmd_manager, AutoCmdManager, VimAutocmd, EmitSpec, PayloadMapper
from pytoy.infra.autocmd.vim_autocmd import EmitterPayload

from pytoy.infra.core.models import Event, EventEmitter
from pytoy.infra.core.models import Event, Listener, Disposable

from typing import Callable, Sequence, Any



_any_win_closed_group = "PytoyAnyWinClosedGroupAutocmd"
_cached_win_closed_event: Event[int] | None = None

def _get_any_win_closed_autocmd() -> VimAutocmd[int]:
    manager = get_autocmd_manager()
    emit_spec = EmitSpec(event="WinClosed")
    payload_mapper = PayloadMapper(arguments=["afile"], transform=lambda args: int(args[0]))
    return manager.register(_any_win_closed_group, emit_spec, payload_mapper)


def _get_base_winclosed_event() -> Event[int]:
    global _cached_win_closed_event
    if _cached_win_closed_event is None:
        autocmd = _get_any_win_closed_autocmd()
        _cached_win_closed_event = autocmd.event
    return _cached_win_closed_event

def get_winclosed_event(winid: int) -> Event[int]:
    base_event = _get_base_winclosed_event()
    return base_event.filter(lambda _id: _id == winid).once()
