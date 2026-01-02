from pytoy.ui.notifications.models import LEVEL, NotificationParam 
from pytoy.ui.notifications.protocol import EphemeralNotificationProtocol
from pytoy.ui.vscode.api import Api
from typing import assert_never
import json

class EphemeralNotificationVSCode(EphemeralNotificationProtocol):
    def notify(
        self,
        message: str,
        param: NotificationParam | LEVEL = "info",
    ) -> None:
        """Note that in vscode, `timeout` is unapplicable.
        """
        if not isinstance(param, NotificationParam):
            param = NotificationParam.from_level(param)
        match param.level:
            case "info":
                funcname = "showInformationMessage"
            case "warning":
                funcname = "showWarningMessage"
            case "error":
                funcname = "showErrorMessage"
            case _:
                assert_never(param.level)

        # NOTE: 
        # By displaying window, the focus changes to the notificiation window. 
        # The following is guess, but this is not checked by `neovim-vscode-plugin`, 
        # Hence, without `await vscode.commands.executeCommand('workbench.action.focusActiveEditorGroup')`, 
        # inconsistency of state occurs in the plugin and go to freeze. 
        api = Api()
        from string import Template
        template = Template("""
        (async () => {
            const p = vscode.window.$funcname($q_message);
            await vscode.commands.executeCommand('workbench.action.focusActiveEditorGroup');
            return "SUCCESS";
        })();
        """)
        jscode = template.substitute(funcname=funcname, q_message=self._quote(message))
        api.eval_with_return(jscode, with_await=True)


    def _quote(self, message: str) -> str:
        return json.dumps(message)
