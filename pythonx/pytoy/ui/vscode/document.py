# Experimental codes related to VSCode
from typing import Self, Literal
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
    def create(cls, uri: Uri) -> Self:
        api = Api()
        js_code = """
        (async (scheme, authority, path) => {

          let uriStr;
          if (authority) {
              uriStr = scheme + "://" + authority + path;
          } else {
              uriStr = scheme + ":" + path;
          }
          const uri = vscode.Uri.parse(uriStr);
          try {
              const doc = await vscode.workspace.openTextDocument(uri);
              return doc;
          } catch (err) {
              // not found → fallback to create new file
              // VSCode cannot create a new (yet-not-existing) file directly by openTextDocument
          }

          // -----------------------------
          // New file creation via WorkspaceEdit
          // -----------------------------
          const edit = new vscode.WorkspaceEdit();
          edit.createFile(uri, { overwrite: false });

          const success = await vscode.workspace.applyEdit(edit);
          if (!success) {
              throw new Error("Failed to create new file: " + uri.toString());
          }

          // Now the file exists
          const newDoc = await vscode.workspace.openTextDocument(uri);
          return newDoc;

        })(args.scheme, args.authority, args.path)
        """
        args = {"args": {"scheme": uri.scheme, "path": uri.path, "authority": uri.authority}}
        ret = api.eval_with_return(js_code, with_await=True, opts=args)
        return cls.model_validate(ret)
      
    @classmethod
    def open(self, uri: Uri, position: tuple[int, int] | None = None):
      """posistion=(lnum, lcol)""" 
      jscode = """
      (async (scheme, path, authority, position) => {
          const separator = authority ? "://" : ":";
          const uriStr = scheme + separator + (authority || "") + path;
          const uri = vscode.Uri.parse(uriStr);
          
          const openOptions = {};

          if (position) {
              const [lnum, lcol] = position;
              if (typeof lnum === 'number' && lnum > 0 && typeof lcol === 'number' && lcol > 0) {
                  // VS CodeのPositionは0-basedなので、-1します。
                  const line = lnum - 1;
                  const character = lcol - 1;

                  const position = new vscode.Position(line, character);
                  openOptions.selection = new vscode.Range(position, position);
              }
          }
          await vscode.commands.executeCommand(
              'vscode.open',
              uri,
              openOptions
          )
      })(args.scheme, args.path, args.authority, args.position)
      """
      api = Api()
      result = api.eval_with_return(
          jscode,
          with_await=True,
            opts={"args": {"path": uri.path, "scheme": uri.scheme, "authority": uri.authority, "position": position}},
        )
      return result

    def append(self, text: str) -> bool:
        """Append text at the end of the document."""
        api = Api()
        js_code = """
        (async (args) => {

          const scheme = args.scheme;
          const path   = args.path;

          const doc = vscode.workspace.textDocuments.find(
              d => d.uri.scheme === scheme && d.uri.path === path
          );

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


          return await vscode.workspace.applyEdit(edit);
      })(args)
      """
        result = api.eval_with_return(
            js_code,
            with_await=True,
            opts={"args": {"path": self.uri.path, "scheme": self.uri.scheme, "text": f"{text}"}},
        )
        return result


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
