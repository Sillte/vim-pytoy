"""This works only when `vscode+nvim`
"""

from pathlib import Path 
from pydantic import BaseModel,ConfigDict

class Api:
    def __init__(self):
        import vim
        vim.exec_lua("_G.vscode_api_global = require('vscode')")
        self._api = vim.lua.vscode_api_global
        #ret = vim.lua.vscode_api_global.eval("return vscode.window.activeTextEditor.document.fileName")
        
    def eval_with_return(self, js_code: str,
                         args: None | dict = None,  
                         with_await: bool=True):
        """Evaluate `js_code` with `args`. 
        Example:
            api.eval_with_return("vscode.window.activeTextEditor.document.fileName",
                               with_await=False)

        """
        if not args:
            args = dict()
        if not with_await:
            ret = self._api.eval(f"return {js_code}", args)
        else:
            ret = self._api.eval(f"return await {js_code}", args)
        return ret
    
class Uri(BaseModel):
    path: str
    scheme: str
    fsPath: str | None = None

    model_config = ConfigDict(extra="allow")
    

class Document(BaseModel):
    uri: Uri
    model_config = ConfigDict(extra="allow")
    
    @classmethod
    def create(cls, path: None | str | Path = None):
        api = Api()
        js_code = """
    (async () => {
      const path = args.path;
      let doc; 
      if (path === undefined || path === null || path === "") {
        doc = await vscode.workspace.openTextDocument({ language: 'plaintext', content: '' });
      } else {
        const uri = vscode.Uri.file(path);
        doc = await vscode.workspace.openTextDocument(uri);
      }
      return doc;
    })()
    """
        if isinstance(path, Path):
            path = path.as_posix()
        args = {"args": {"path": path}}
        doc = api.eval_with_return(js_code, with_await=True, args=args)
        return Document(**doc) 
    
    @classmethod
    def from_path(cls, path: str | Path):
        js_code = """
        (async () => {
          const path = args.path;
          let doc;

          if (path === undefined || path === null || path === "") {
            doc = await vscode.workspace.openTextDocument({ language: 'plaintext', content: '' });
          } else {
            const uri = vscode.Uri.file(path);
            doc = await vscode.workspace.openTextDocument(uri);
          }
          return doc;
        })()
        """
        api = Api()
        args = {"args": {"path": str(path)}}
        doc = api.eval_with_return(js_code, with_await=True, args=args)
        return doc
    
    def append(self, text:str):
        """Append text at the end of the document.
        """
        api = Api()
        js_code = """
        (async () => {
        const path = args.path; 
      const text = args.text;

      const doc = vscode.workspace.textDocuments.find(
        d => d.isUntitled && d.uri.path === path
      );

      if (!doc) {
        return { success: false, message: "Untitled document not found." };
      }

      const edit = new vscode.WorkspaceEdit();
      const pos = new vscode.Position(doc.lineCount, 0);
      edit.insert(doc.uri, pos, text);

      const ok = await vscode.workspace.applyEdit(edit);
      return {
        success: ok,
        message: ok ? "Appended to untitled." : "Edit failed."
      };
    })()
      """
        result = api.eval_with_return(js_code, with_await=True, args={
        "args": {
            "path": self.uri.path,
            "text": f"{text}\n"
                }
              })
        return result
      
    @property
    def content(self) -> str:   
      """Return the string of document.
      """
      api = Api()
      js_code = """
        (async () => {
        const path = args.path; 
      const doc = vscode.workspace.textDocuments.find(
        d => d.isUntitled && d.uri.path === path
      );

      if (!doc) {
        return "Untitled document not found.";
      }
      const fullText = doc.getText();
      return fullText;
    })()
    """
      result = api.eval_with_return(js_code, with_await=True, args={
        "args": { "path": self.uri.path, } })
      return result
    
    def show(self):
      api = Api()
      js_code = """
      (async () => {
      const path = args.path;

      const doc = vscode.workspace.textDocuments.find(
        d => d.uri.path == path
      );


      if (!doc) {
        return { success: false, message: "Untitled document not found." };
      }

      await vscode.window.showTextDocument(doc, { preview: false });
      return { success: true, message: "Untitled document shown." };
    })()
      """
      args = {"args": {"path": self.uri.path}}

      result = api.eval_with_return(js_code, with_await=True, args=args)
      return result 


def get_uris() -> list[Uri]:
    """Return the `fsPaths`. 
    """
    api = Api()
    js_code = """
    (async () => {
        var array = [];
        for (const doc of vscode.workspace.textDocuments) {
          array.push(doc.uri);
        }
        return array
    })()
    """
    return [Uri(**elem) for elem in api.eval_with_return(js_code, with_await=True)]


def delete_untitles():
    """Delete `untitle` documents without warning.
    """
    api = Api()
    js_code = """
(async () => {
  for (const doc of vscode.workspace.textDocuments) {
    if (doc.isUntitled) {
      const editors = vscode.window.visibleTextEditors.filter(e => e.document === doc);
      if (editors.length > 0) {
        await vscode.window.showTextDocument(doc, { preview: false });
        await vscode.commands.executeCommand('workbench.action.revertAndCloseActiveEditor');
      } else {
        const editor = await vscode.window.showTextDocument(doc, { preview: false });
        await vscode.commands.executeCommand('workbench.action.revertAndCloseActiveEditor');
      }
    }
  }
})();
"""
    return api.eval_with_return(js_code, with_await=True)
