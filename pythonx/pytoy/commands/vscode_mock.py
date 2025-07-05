from pytoy.command import CommandManager, OptsArgument
from pytoy.ui import get_ui_enum, UIEnum 

from pytoy import TERM_STDOUT

if get_ui_enum() == UIEnum.VSCODE:
    from pytoy.ui.vscode.api import Api
    from pytoy.ui.vscode.document import Api, Uri, Document
    from pytoy.ui.vscode.focus_controller import get_uri_to_views

    def script():
        jscode = """
        (async () => {
        return vscode.commands.getCommands(true)
        //await vscode.commands.executeCommand('workbench.action.focusNextGroup');
        //const sleep = (time) => new Promise((resolve) => setTimeout(resolve, time));
        //await sleep(10)
        })()
        """
        return jscode


    @CommandManager.register(name="MOCK", range=True)
    class CommandFunctionClass1:
        def __call__(self, opts: OptsArgument):
            # api = Api()
            scheme = "untitled"

            uri = Uri(path=TERM_STDOUT, scheme="untitled")
            uri_to_views = get_uri_to_views()
            if uri in uri_to_views:
                doc = Document(uri=uri)
            else:
                pass


    @CommandManager.register(name="MOCKA", range=True)
    class CommandFunctionClass:
        def __call__(self, opts: OptsArgument):
            api = Api()
            commands = api.eval_with_return(
                "vscode.commands.executeCommand('github.copilot.chat.explain');",
                with_await=True,
            )
            print(commands)
