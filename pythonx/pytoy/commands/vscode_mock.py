from pytoy.command import CommandManager, OptsArgument
from pytoy.ui import get_ui_enum, UIEnum 

from pytoy import TERM_STDOUT

@CommandManager.register(name="MyWindow", range=True)
def mywindow_func():
    from pytoy.ui.pytoy_window import PytoyWindow
    window = PytoyWindow.get_current()
    print(window.valid)
    buffer = window.buffer
    if buffer:
        print(buffer.content)
    print(window.is_left())
    

if get_ui_enum() == UIEnum.VSCODE:
    from pytoy.ui.vscode.api import Api
    from pytoy.ui.vscode.document import Api, Uri, Document
    from pytoy.ui.vscode.editor import Editor
    from pytoy.ui.vscode.focus_controller import get_uri_to_views
    from pydantic import BaseModel, ConfigDict
    from pprint import pprint


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
            #api = Api()
            #data = api.eval_with_return("vscode.window.activeTextEditor", with_await=False)
            #pprint(data)
            print(Editor.get_current())
            return
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
