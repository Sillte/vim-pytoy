from typing import Protocol, Literal
from pytoy.ui.notifications.models import NotificationParam, LEVEL


class EphemeralNotificationProtocol(Protocol):
    def notify(
        self,
        message: str,
        param: NotificationParam | LEVEL = "info",  
    ) -> None:
        ...
