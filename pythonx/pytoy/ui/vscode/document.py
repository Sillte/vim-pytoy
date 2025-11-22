# Experimental codes related to VSCode
from typing import Self
from pathlib import Path
from pydantic import BaseModel, ConfigDict

from pytoy.ui.vscode.api import Api
from pytoy.ui.vscode.uri import Uri


class Document(BaseModel):
    uri: Uri
    model_config = ConfigDict(extra="allow")

    @classmethod
    def get_current(cls) -> Self:
        api = Api()
        doc = api.eval_with_return(
            "vscode.window.activeTextEditor.document", with_await=False
        )
        return cls.model_validate(doc)

    @classmethod
    def create(cls, path: None | str | Path = None) -> Self:
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
        doc = api.eval_with_return(js_code, with_await=True, opts=args)
        return cls.model_validate(doc)

    def append(self, text: str) -> bool:
        """Append text at the end of the document."""
        api = Api()
        js_code = """
        (async () => {
        const path = args.path; 

          const doc = vscode.workspace.textDocuments.find(
          d => d.uri.path === path
          );

      if (!doc) {
        return { success: false, message: "Untitled document not found." };
      }

        const edit = new vscode.WorkspaceEdit();

        let pos;
        if (doc.lineCount === 0) {
          pos = new vscode.Position(0, 0);
        } else {
          const lastLine = doc.lineCount - 1;
          const lastLineText = doc.lineAt(lastLine).text;
          pos = new vscode.Position(lastLine, lastLineText.length);
        }

        edit.insert(doc.uri, pos, args.text);


      const ok = await vscode.workspace.applyEdit(edit);
      return {
        success: ok,
        message: ok ? "Appended to untitled." : "Edit failed."
      };
    })()
      """
        result = api.eval_with_return(
            js_code,
            with_await=True,
            opts={"args": {"path": self.uri.path, "text": f"{text}"}},
        )
        return bool(result["success"])


    @property
    def content(self) -> str:
        """Return the string of document."""
        api = Api()
        js_code = """
        (async () => {
        const path = args.path; 
      const doc = vscode.workspace.textDocuments.find(
        d => d.uri.path === path
      );

      if (!doc) {
        return "Untitled document not found.";
      }
      const fullText = doc.getText();
      return fullText;
    })()
    """
        result = api.eval_with_return(
            js_code,
            with_await=True,
            opts={
                "args": {
                    "path": self.uri.path,
                }
            },
        )
        return result

    @content.setter
    def content(self, value: str) -> None:
        api = Api()
        js_code = """
        (async (path, content) => {
          const doc = vscode.workspace.textDocuments.find(
                d => d.uri.path === path
            );
          if (!doc) {
              return false;
          }
    
          // 2. WorkspaceEditを作成
          const edit = new vscode.WorkspaceEdit();

          // 3. ドキュメント全体を対象とするRangeを計算
          const fullRange = new vscode.Range(
              doc.positionAt(0),
              doc.positionAt(doc.getText().length)
          );

          // 4. WorkspaceEditに対象ドキュメント全体を削除し、新しい内容を挿入する編集操作を追加
          edit.delete(doc.uri, fullRange); 
          //   - 0, 0の位置に新しい内容を挿入
          edit.insert(doc.uri, new vscode.Position(0, 0), content);
          
          // 5. 編集を適用 (awaitで同期を取る)
          const success = await vscode.workspace.applyEdit(edit);

          // 6. 成功を返す
          return success;
      
    })(args.path, args.value)
    """
        result = api.eval_with_return(
            js_code,
            with_await=True,
            opts={"args": {"path": self.uri.path, "value": value}},
        )
        return result

    def show(self, with_focus: bool = False) -> None:
        api = Api()
        js_code = """
    (async (uri, preserveFocus) => {
    async function showDocumentIfVisibleOrOpen(uri) {
    const visibleEditor = vscode.window.visibleTextEditors.find(
      editor => editor.document.uri.toString() === uri.toString()
    );

    if (visibleEditor) {
      return await vscode.window.showTextDocument(visibleEditor.document, {
        viewColumn: visibleEditor.viewColumn,
        preserveFocus: preserveFocus,
        preview: false
      });
      }
    return null;
    }
    return await showDocumentIfVisibleOrOpen(uri);
    })(args.uri, args.preserveFocus)
      """
        args = {"args": {"uri": dict(self.uri), "preserveFocus": not with_focus}}

        result = api.eval_with_return(js_code, with_await=True, opts=args)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Document):
            return NotImplemented
        return self.uri == other.uri