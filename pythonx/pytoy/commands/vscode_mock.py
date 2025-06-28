from pytoy.command import CommandManager, OptsArgument 

from pytoy.ui.vscode.api import Api
from pytoy.ui.vscode.document import Api, Uri, Document, get_uris, BufferURISolver
from pytoy.ui.vscode.document_user import sweep_editors, make_document
from pytoy.ui.vscode.focus_controller import get_uri_to_views
from pytoy.ui.pytoy_buffer import PytoyBuffer, PytoyBufferVSCode
from pytoy.infra.timertask import TimerTask  
import vim
import os
from pytoy.lib_tools.buffer_executor import BufferExecutor
from pytoy import TERM_STDOUT
from pathlib import Path
from pytoy.environment_manager import EnvironmentManager
from pytoy.ui import make_buffer



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
class CommandFunctionClass:
    def __call__(self, opts: OptsArgument):
        # api = Api()
        scheme = "untitled"
        
        uri = Uri(path=TERM_STDOUT, scheme="untitled")
        uri_to_views = get_uri_to_views()
        if uri in uri_to_views:
            doc = Document(uri=uri)
        else:
            pass
            

        #commands = api.eval_with_return(script())
        #uri = make_document(TERM_STDOUT)
        #doc = Document(uri=uri)
        #impl = PytoyBufferVSCode(doc)
        #buffer = PytoyBuffer(impl)
        #buffer.init_buffer()
        #buffer.append("\n".join(commands))
        # return 


@CommandManager.register(name="MOCKA", range=True)
class CommandFunctionClass:
    def __call__(self, opts: OptsArgument):
        api = Api()
        commands = api.eval_with_return("vscode.commands.executeCommand('github.copilot.chat.explain');", with_await=True)
        print(commands)
