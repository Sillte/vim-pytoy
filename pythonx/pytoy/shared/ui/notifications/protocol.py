from typing import Protocol

from pytoy.shared.ui.notifications.models import LEVEL, NotificationParam


class EphemeralNotificationProtocol(Protocol):
    def notify(
        self,
        message: str,
        param: NotificationParam | LEVEL = "info",
    ) -> None: ...
