from pytoy.command import CommandManager

from pytoy.ui_pytoy.vscode.api import Api
from pytoy.ui_pytoy.vscode.document import Api, Uri, Document, get_uris
from pytoy.ui_pytoy.vscode.document_user import sweep_editors
from pytoy.ui_pytoy.pytoy_quickfix import QuickFixController
from pytoy.timertask_manager import TimerTaskManager  

import vim


def script():
    jscode = """
    (async () => {
    await vscode.commands.executeCommand('workbench.action.focusNextGroup');
    const sleep = (time) => new Promise((resolve) => setTimeout(resolve, time));
    //await sleep(10)
    })()
    """
    return jscode
    pass

@CommandManager.register(name="NAIVE")
def func_naive():
    api = Api()
    QuickFixController.next()
    return 


    from pytoy.ui_pytoy.vscode.focus_controller  import Api, get_active_viewcolumn, store_focus
    from pytoy.ui_pytoy.vscode.focus_controller  import set_active_viewcolumn

    api = Api()

    import time
    set_active_viewcolumn(2)
    time.sleep(1.0)
    set_active_viewcolumn(1)
    active_column = api.eval_with_return("vscode.window.activeTextEditor.viewColumn",
                                         with_await=False)
    active_column = get_active_viewcolumn()
    print("ret_active_view", active_column, type(active_column))
    with store_focus():
        #api.action("workbench.action.focusNextGroup")

        pass

#@CommandManager.register(name="Qnext")
#def q_next():
#    QuickFixController.next()
#
#@CommandManager.register(name="Qprev")
#def q_prev():
#    QuickFixController.prev()
#
#@CommandManager.register(name="QQ")
#def QQ():
#    QuickFixController.go()
#
#
#@CommandManager.register(name="OnlyThisEditor")
#def only_this_editor():
#    #await vscode.commands.executeCommand('workbench.action.focusNextGroup');
#    api = Api()
#    sweep_editors() 
#
#

