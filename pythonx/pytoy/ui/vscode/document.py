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
        (async (uriKey) => {
          const uri = vscode.Uri.parse(uriKey);

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

        })(args.uriKey)
        """
        args = {"args": {"uriKey": uri.to_key_str()}}
        ret = api.eval_with_return(js_code, with_await=True, opts=args)
        return cls.model_validate(ret)
      
    @classmethod
    def open(cls, uri: Uri, position: tuple[int, int] | None = None) -> Self:
      """posistion=(lnum, lcol)""" 
      jscode = """
      (async (uriKey, position) => {
          const uri = vscode.Uri.parse(uriKey);
          const doc = await vscode.workspace.openTextDocument(uri);
          
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
          await vscode.window.showTextDocument( doc, openOptions);
          return doc;

      })(args.uriKey, args.position)
      """
      api = Api()
      result = api.eval_with_return(
          jscode,
          with_await=True,
            opts={"args": {"uriKey": uri.to_key_str(), "position": position}},
        )
      return cls.model_validate(result)

    def append(self, text: str) -> bool:
        """Append text at the end of the document."""
        api = Api()
        js_code = """
        (async (args) => {
            const uriKey = args.uriKey;
            const text = args.text;

            const uri = vscode.Uri.parse(uriKey);

            const doc = await vscode.workspace.openTextDocument(uri);
            
            let pos;
            if (doc.lineCount === 0) {
                // ドキュメントが空の場合、(0, 0)
                pos = new vscode.Position(0, 0);
            } else {
                // 最終行の行番号と、最終行のテキストの長さを取得
                const lastLine = doc.lineCount - 1;
                const lastLineText = doc.lineAt(lastLine).text;
                pos = new vscode.Position(lastLine, lastLineText.length);
            }

            const edit = new vscode.WorkspaceEdit();
            edit.insert(doc.uri, pos, text);

            return await vscode.workspace.applyEdit(edit);
        })(args)
        """
      
        result = api.eval_with_return(
            js_code,
            with_await=True,
            opts={"args": {"uriKey": self.uri.to_key_str(), "text": text}},
        )
        return result


    @property
    def content(self) -> str:
        """Return the string of document."""
        api = Api()
        js_code = """
        (async (args) => {
            const uri = vscode.Uri.parse(args.uriKey);
            const doc = await vscode.workspace.openTextDocument(uri);
            return doc.getText();
        })(args)
        """
        result = api.eval_with_return(
            js_code,
            with_await=True,
            opts={
                "args": {
                    "uriKey": self.uri.to_key_str(), 
                }
            },
        )
        return result

    @content.setter
    def content(self, value: str):
        api = Api()
        js_code = """
        (async (args) => {
            const uri = vscode.Uri.parse(args.uriKey);
            const content = args.content;
            
            try {
                const doc = await vscode.workspace.openTextDocument(uri);
                
                const edit = new vscode.WorkspaceEdit();
                
                const startPos = doc.positionAt(0);
                const endPos = doc.positionAt(doc.getText().length); 
                
                const fullRange = new vscode.Range(startPos, endPos);
                edit.replace(doc.uri, fullRange, content);

                await vscode.workspace.applyEdit(edit);
                
            } catch (err) {
                console.error("Failed to set content: ", err, uri);
            }

        })(args)
        """
   
        api.eval_with_return(
            js_code,
            with_await=True,
            opts={"args": {"uriKey": self.uri.to_key_str(), "content": value}},
        )


    def show(self, with_focus: bool = False):
        api = Api()
        js_code = """
    (async (uriKey, preserveFocus) => {
        function IsSameDocument(targetUri, editorUri) {
                const targetAuthority = targetUri.authority || "";
                const targetPath = targetUri.path;
                
                const docAuthority = editorUri.authority || "";
                const docPath = editorUri.path;
                
                return targetUri.scheme === editorUri.scheme &&
                       targetAuthority === docAuthority &&
                       targetPath === docPath;
            }

        const uri = vscode.Uri.parse(uriKey);

        //If already, the editor is visible, it is prioritized.
        const visibleEditor = vscode.window.visibleTextEditors.find(
                    editor => IsSameDocument(uri, editor.document.uri)
                );
        if (visibleEditor) {
            return await vscode.window.showTextDocument(visibleEditor.document, {
                viewColumn: visibleEditor.viewColumn,
                preserveFocus: preserveFocus,
                preview: false
            });
        }

        // If there is no editors, `newly` opened.
        let doc; 
        try {
            doc = await vscode.workspace.openTextDocument(uri);
        } catch (err) {
          console.log("Cannot find", uri)
          return; 
        }

        return await vscode.window.showTextDocument(doc, {
        preserveFocus: preserveFocus,
        preview: false
      });
    })(args.uriKey, args.preserveFocus)
      """
        args = {"args": {"uriKey": self.uri.to_key_str(), "preserveFocus": not with_focus}}
        api.eval_with_return(js_code, with_await=True, opts=args)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Document):
            return NotImplemented
        return self.uri == other.uri