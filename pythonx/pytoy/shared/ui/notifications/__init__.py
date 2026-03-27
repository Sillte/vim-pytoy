from pytoy.shared.ui.notifications.models import LEVEL, NotificationParam
from pytoy.shared.ui.notifications.protocol import EphemeralNotificationProtocol     
from pytoy.shared.lib.backend import get_backend_enum, BackendEnum

class EphemeralNotification(EphemeralNotificationProtocol):
    def __init__(self, impl: EphemeralNotificationProtocol | None = None) -> None:
        if impl is None:
            impl = _get_implementation() 
        self._impl = impl

    @property
    def impl(self) -> EphemeralNotificationProtocol: 
        return self._impl

    def notify(
        self,
        message: str,
        param: NotificationParam | LEVEL = "info",  
    ) -> None:
        return self._impl.notify(message, param)
        

def _get_implementation() -> EphemeralNotificationProtocol:
    backend_enum = get_backend_enum()
    if backend_enum == BackendEnum.VIM:
        from pytoy.shared.ui.notifications.impls.vim import EphemeralNotificationVim
        return EphemeralNotificationVim()
    elif backend_enum == BackendEnum.NVIM:
        from pytoy.shared.ui.notifications.impls.nvim import EphemeralNotificationNVim
        return EphemeralNotificationNVim()
    elif backend_enum == BackendEnum.VSCODE:
        from pytoy.shared.ui.notifications.impls.vscode import EphemeralNotificationVSCode
        return EphemeralNotificationVSCode()
    else:
        from pytoy.shared.ui.notifications.impls.dummy import EphemeralNotificationDummy
        return EphemeralNotificationDummy()


