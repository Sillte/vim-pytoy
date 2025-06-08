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
    #QuickFixController.go()
    #TimerTaskManager.execute_oneshot(f, 100)
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

@CommandManager.register(name="Qnext")
def Qnext():
    #await vscode.commands.executeCommand('workbench.action.focusNextGroup');
    QuickFixController.next()

@CommandManager.register(name="Qprev")
def Qprev():
    #await vscode.commands.executeCommand('workbench.action.focusNextGroup');
    QuickFixController.prev()

@CommandManager.register(name="QQ")
def QQ():
    #await vscode.commands.executeCommand('workbench.action.focusNextGroup');
    QuickFixController.go()



@CommandManager.register(name="OnlyThisEditor")
def only_this_editor():
    #await vscode.commands.executeCommand('workbench.action.focusNextGroup');
    api = Api()
    sweep_editors() 


@CommandManager.register(name="VS")
def func():
    import pytoy
    import vim
    import time
    #vim.command("Vsplit")
    import vim
    api = Api()

    #print("ret", ret)
    return 



OPEN_WINDOW =     """(async() =>  {
    async function createWindow(bufname = "NAME", mode = "vertical", baseViewColumn = vscode.ViewColumn.Active) {
    // step 1: create a new untitled text document (like new buffer)
    const doc = await vscode.workspace.openTextDocument({ 
        content: "", 
        language: "plaintext" // 適宜変更可
    });
    vscode.window.showInformationMessage("message" + baseViewColumn.toString());

    // step 2: determine where to show (vertical or horizontal split)
    const viewColumn = getSplitColumn(baseViewColumn, mode);

    // step 3: show it in editor (acts like open buffer in split)
    const editor = await vscode.window.showTextDocument(doc, { viewColumn, preview: false });

    return editor;
}

function getSplitColumn(baseColumn, mode) {
    return vscode.ViewColumn.Beside;
    if (mode.startsWith("v")) {
        return baseColumn === vscode.ViewColumn.One ? vscode.ViewColumn.Two : vscode.ViewColumn.Three;
    } else {
        return vscode.ViewColumn.Beside;
    }
}
createWindow(); 
})()
"""
