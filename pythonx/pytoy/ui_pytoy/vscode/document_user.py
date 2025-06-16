from pathlib import Path
import vim
from pytoy.ui_pytoy.vscode.api import Api
from pytoy.ui_pytoy.vscode.document import Uri, BufferURISolver, Document
from pytoy.ui_pytoy.vscode.utils import wait_until_true

def _current_uri_check(name) -> bool:
    api = Api()
    
    uri = api.eval_with_return(
        "vscode.window.activeTextEditor?.document?.uri ?? null", with_await=False
    )
    if uri:
        return Path(Uri(**uri).path).name == name
    return False
  
def make_document(name: str) -> Document:
  """Making a document from name.
  """
  api = Api()
  vim.command("Vsplit")
  vim.command(f"Edit {name}")

  wait_until_true(lambda: _current_uri_check(name), timeout=0.3)

  uri = api.eval_with_return(
      "vscode.window.activeTextEditor.document.uri", with_await=False
  )
  uri = Uri(**uri)
  wait_until_true(lambda:  BufferURISolver.get_bufnr(uri) != None, timeout=0.3)
  vim.command("Tabonly")
  return Document(uri=uri)


def make_duo_documents(name1: str, name2: str) -> tuple[Document, Document]:
    api = Api()
    vim.command("Vsplit")
    vim.command(f"Edit {name1}")


    wait_until_true(lambda: _current_uri_check(name1), timeout=0.3)
    uri1 = api.eval_with_return(
        "vscode.window.activeTextEditor.document.uri", with_await=False
    )
    uri1 = Uri(**uri1)

    vim.command("Tabonly")
    vim.command("Split")
    vim.command(f"Edit {name2}")
    wait_until_true(lambda: _current_uri_check(name2), timeout=0.3)
    uri2 = api.eval_with_return(
        "vscode.window.activeTextEditor.document.uri", with_await=False
    )

    uri2 = Uri(**uri2)
    vim.command("Tabonly")

    return (Document(uri=uri1), Document(uri=uri2))


def sweep_editors(names = None):
    js_code= """(async(names = []) => {
    async function clearUntitledDocs(names = []) {
      const allDocs = vscode.workspace.textDocuments;

      for (const doc of allDocs) {
        if (
          doc.uri.scheme === "untitled" &&
          doc.isDirty &&
          doc.getText().length > 0
        ) {
          const baseName = doc.uri.path.startsWith("/") ? doc.uri.path.slice(1) : doc.uri.path;

          if (names.length === 0 || names.includes(baseName)) {
            const editor = vscode.window.visibleTextEditors.find(e => e.document === doc);
            if (editor) {
              await editor.edit(editBuilder => {
                const lastLine = doc.lineCount - 1;
                const fullRange = new vscode.Range(
                  new vscode.Position(0, 0),
                  doc.lineAt(lastLine).range.end
                );
                editBuilder.delete(fullRange);
              });
            }
          }
        }
      }

  await vscode.commands.executeCommand('workbench.action.closeEditorsInOtherGroups');
}
clearUntitledDocs(names)
 })(args.names)
 """
    if names is None:
        names = []
    api = Api()
    api.eval_with_return(js_code, args={"args": {"names": names}}, with_await=True)

    # As you notice, if the warning appears, 
    def _is_unique_editor():
      number = api.eval_with_return("vscode.window.visibleTextEditors.length", with_await=False)
      if number <= 1:
        return True
      return False
    return wait_until_true(_is_unique_editor, 0.3)
