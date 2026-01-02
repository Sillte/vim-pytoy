import vim
from typing import Mapping, Any
import json
from pytoy.ui.notifications.models import LEVEL, NotificationParam 
from pytoy.ui.notifications.protocol import EphemeralNotificationProtocol      

class EphemeralNotificationVim(EphemeralNotificationProtocol):
    def notify(
        self,
        message: str,
        param: NotificationParam | LEVEL = "info",  
    ) -> None:
        """Note that this is unaviable in `NVIM`.
        """

        if not isinstance(param, NotificationParam):  
            param = NotificationParam.from_level(param) 

        timeout = param.timeout if param.timeout is not None else 3000

        # highlight
        hl = {
            "info": "Normal",
            "warning": "WarningMsg",
            "error": "ErrorMsg",
        }[param.level]

        # Surely, it is better rot `dataclasses.dataclass`, 
        # But it is after the specification is fixed.
        opts = {
            "line": int(vim.eval("&lines")) - 2,
            "col": int(vim.eval("&columns")),
            "pos": "botright",        
            "time": timeout,
            "highlight": hl,
            "padding": [0, 1, 0, 1],
            "border": [1, 1, 1, 1],    
            "borderchars": ['─', '│', '─', '│', '┌', '┐', '┘', '└'], # 枠線の文字指定
            "borderhighlight": [hl],   # 枠線の色もメッセージに合わせる
        }

        if int(vim.eval("exists('*popup_create')")):
            popup_create = vim.Function("popup_create")
            popup_create(message, opts)
        else:
            print(message)
            popup_create = None


