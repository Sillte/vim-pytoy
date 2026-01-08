from pytoy.ui.notifications.models import LEVEL, NotificationParam
from pytoy.ui.notifications.protocol import EphemeralNotificationProtocol     
from pytoy.ui.ui_enum import get_ui_enum, UIEnum

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
    ui_enum = get_ui_enum()
    if ui_enum == UIEnum.VIM:
        from pytoy.ui.notifications.impls.vim import EphemeralNotificationVim
        return EphemeralNotificationVim()
    elif ui_enum == UIEnum.NVIM:
        from pytoy.ui.notifications.impls.nvim import EphemeralNotificationNVim
        return EphemeralNotificationNVim()
    elif ui_enum == UIEnum.VSCODE:
        from pytoy.ui.notifications.impls.vscode import EphemeralNotificationVSCode
        return EphemeralNotificationVSCode()
    else:
        raise RuntimeError("Implementation Error")


