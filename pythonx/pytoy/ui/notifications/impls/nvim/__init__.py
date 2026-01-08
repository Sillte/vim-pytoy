from pytoy.ui.notifications.models import LEVEL, NotificationParam 
from pytoy.ui.notifications.protocol import EphemeralNotificationProtocol      

class EphemeralNotificationNVim(EphemeralNotificationProtocol):
    def notify(
        self,
        message: str,
        param: NotificationParam | LEVEL = "info",  
    ) -> None:
        if not isinstance(param, NotificationParam):  
            param = NotificationParam.from_level(param) 
        print(message)
