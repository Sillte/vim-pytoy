import vim
from typing import Mapping, Any
import json
from pytoy.shared.ui.notifications.models import LEVEL, NotificationParam 
from pytoy.shared.ui.notifications.protocol import EphemeralNotificationProtocol      

class EphemeralNotificationDummy(EphemeralNotificationProtocol):
    def notify(
        self,
        message: str,
        param: NotificationParam | LEVEL = "info",  
    ) -> None:
        """Note that this is unaviable in `NVIM`.
        """
        print("NOTIFICATION", message)

