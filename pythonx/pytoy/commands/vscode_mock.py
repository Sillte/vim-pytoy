from pytoy.command import CommandManager, OptsArgument
from pytoy.ui import get_ui_enum, UIEnum 
import vim 


@CommandManager.register(name="MyWindow", range=True)
def mywindow_func():
    from pytoy.ui.pytoy_window import PytoyWindow, PytoyWindowProvider
    from pytoy.ui.vscode.editor import Editor
    window = PytoyWindow.get_current()
    PytoyWindowProvider().create_window("hgoehoge", "s")
    print(window.buffer)
    print(window.buffer.content)
    window.focus()
    #windows[0].impl.editor.focus()
    #print(window.valid, window.impl.editor.document.uri)
    #window.buffer
    #window.unique()    



from pytoy.lib_tools.terminal_backend import TerminalBackendProvider
from pytoy.lib_tools.terminal_executor import TerminalExecutor
from pytoy.ui.pytoy_buffer import PytoyBuffer, make_buffer

from pytoy.command import CommandManager, OptsArgument 

class CommandTerminal:
    name = "__command__"

    executor = None

    @staticmethod
    def get_executor():
        if CommandTerminal.executor:
            return CommandTerminal.executor
        buffer = make_buffer(CommandTerminal.name)
        backend = TerminalBackendProvider().make_terminal(command="cmd.exe")
        executor = TerminalExecutor(buffer, backend)
        CommandTerminal.executor = executor
        return executor


    @CommandManager.register(name="MockCMDStart")
    @staticmethod
    def start():
        executor = CommandTerminal.get_executor()
        executor.start()

    @CommandManager.register(name="MockCMDSend", range=True)
    @staticmethod
    def send(opts: OptsArgument):
        executor = CommandTerminal.get_executor()
        if not executor.alive:
            executor.start()

        cmd = opts.args
        line1, _ = opts.line1, opts.line2
        if not cmd.strip():
            cmd = vim.eval(f"getline({line1})")
        executor.send(cmd)
    

if get_ui_enum() == UIEnum.VSCODE:
    from pytoy.ui.vscode.api import Api
    from pytoy.ui.vscode.document import Api, Uri, Document
    from pytoy.ui.vscode.editor import Editor
    from pydantic import BaseModel, ConfigDict
    from pprint import pprint


    def script():
        jscode = """
        (async () => {
        return vscode.commands.getCommnds(true)
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
            for elem in Editor.get_editors():
                print(elem)

            #editor = Editor.get_current()
            #print("result", editor.close())
            #return
            #scheme = "untitled"

            #uri = Uri(path=TERM_STDOUT, scheme="untitled")
            #uri_to_views = get_uri_to_views()
            #if uri in uri_to_views:
            #    doc = Document(uri=uri)
            #else:
            #   pass

    @CommandManager.register(name="MOCKA", range=True)
    class CommandFunctionClass:
        def __call__(self, opts: OptsArgument):
            api = Api()
            commands = api.eval_with_return(
                "vscode.commands.executeCommand('github.copilot.chat.explain');",
                with_await=True,
            )
            print(commands)
