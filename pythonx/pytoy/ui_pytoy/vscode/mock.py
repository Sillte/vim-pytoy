# Experimental codes related to VSCode  

import vim
from pathlib import Path
from pytoy.ui_pytoy.vscode.api import Api
from pytoy.ui_pytoy.vscode.document import Api, get_uris, delete_untitles
from pytoy.ui_pytoy.vscode.document import Document, BufferURISolver, Uri
from pytoy.ui_pytoy.vscode.utils import  wait_until_true

def make_duo_documents(name1: str, name2: str):
    from pathlib import Path
    import vim
    api = Api()
    vim.command("Vsplit")
    vim.command(f"Edit {name1}")
    def _current_uri_check(name):
        try:
            uri = api.eval_with_return("vscode.window.activeTextEditor.document.uri",
                                        with_await=False)
            return Path(Uri(**uri).path).name == name
        except Exception as e:
            return False

    wait_until_true(lambda: _current_uri_check(name1), timeout=0.3)
    uri1 = api.eval_with_return("vscode.window.activeTextEditor.document.uri",
                               with_await=False)
    uri1 = Uri(**uri1)
    vim.command("Tabonly")

    vim.command("Split")
    vim.command(f"Edit {name2}")
    flag = wait_until_true(lambda: _current_uri_check(name2), timeout=0.3)
    print("flag" ,flag)
    uri2 = api.eval_with_return("vscode.window.activeTextEditor.document.uri",
                               with_await=False)

    uri2 = Uri(**uri2)
    vim.command("Tabonly")

    return [uri1, uri2]

from contextlib import contextmanager 

def get_active_viewcolumn() -> int | None:
    api = Api()
    try:
        active_column = api.eval_with_return("vscode.window.activeTextEditor.viewColumn",
                               with_await=False)
    except Exception as e: 
        print(e)
        return None
    return active_column

def set_active_viewcolumn(viewcolumn: int):
    api = Api()
    jscode = """
    (async (column) => {
  function getEditorInColumn(column) {
    return vscode.window.visibleTextEditors.find(e => e.viewColumn === column);
  }

  async function focusEditor(editor) {
    await vscode.window.showTextDocument(editor.document,  {
      viewColumn: editor.viewColumn,
      preserveFocus: false,
      preview: false
    });
  }
  async function focusEditorByColumn(column) {
    const editor = getEditorInColumn(column);
    if (editor) {
      await focusEditor(editor);
    }
    else {
        await vscode.window.showInformationMessage('NOT Existing!');
    }
  }
      return await focusEditorByColumn(column);
    })(args.column)
    """
    args = {"args": {"column":  int(viewcolumn)}}
    api.eval_with_return(jscode, with_await=True, args=args)


def get_active_uri() -> Uri  | None:
    api = Api()
    try:
        uri = api.eval_with_return("vscode.window.activeTextEditor.document.uri",
                                    with_await=False)
    except Exception as e: 
        return None
    return Uri(**uri)


@contextmanager
def store_focus():
    viewcolumn = get_active_viewcolumn()
    uri = get_active_uri()

    try:
        yield (viewcolumn, uri)
    except Exception as e: 
        raise e
    
    if viewcolumn is not None:
        set_active_viewcolumn(viewcolumn)
    else:
        print("Viewcolumn is None.")

    if uri: 
        bufnr = BufferURISolver.get_bufnr(uri)
        vim.command(f"buffer {bufnr}")
    else:
        print("uri is None.")

if __name__ == "__main__":
    pass
    
#    js_code = """
#    (async (name1, name2) =>  {
#     async function openOrReuseUntitledDoc(uri) {
#        const existing = vscode.workspace.textDocuments.find(doc => doc.uri.path == uri.path);
#       if (!existing){
#        await vscode.window.showInformationMessage('NOT Existing!');
#        }
#        return existing ?? await vscode.workspace.openTextDocument(uri);
#    }
#    async function MakeDuoBuffers(name1, name2) {
#    const activeEditor = vscode.window.activeTextEditor;
#    const activeDocument = activeEditor?.document;
#    if (!activeDocument){
#        vscode.window.showInformationMessage('No active text editor found!');
#        return; 
#    }
#    await vscode.commands.executeCommand('workbench.action.closeEditorsInOtherGroups');
#
#    const UNTITLED_SCHEME = "untitled:"
#
#    const uri1 = vscode.Uri.parse(UNTITLED_SCHEME + name1);
#    const uri2 = vscode.Uri.parse(UNTITLED_SCHEME + name2);
#    const doc1 = await openOrReuseUntitledDoc(uri1);
#    const editor = await vscode.window.showTextDocument(doc1, {
#        viewColumn: vscode.ViewColumn.Beside, 
#        preview : false,
#    });
#
#   await vscode.commands.executeCommand('workbench.action.splitEditorDown');
#
#   const doc2 = await openOrReuseUntitledDoc(uri2);
#
#   setTimeout(async () => {
#        await vscode.window.showTextDocument(doc2);
#        await vscode.commands.executeCommand('workbench.action.focusFirstEditorGroup');
#    }, 20)
#    return [uri1, uri2]
# }
#    try {
#        const result = await MakeDuoBuffers(name1, name2);
#        return await MakeDuoBuffers(name1, name2);
#    } catch (error) {
#        vscode.window.showErrorMessage("MakeDuoBuffers 中にエラーが発生しました: " + error.message);
#    }
#})(args.name1, args.name2)
#"""
#    pass
#
