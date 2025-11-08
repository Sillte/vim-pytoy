# Experimental codes related to VSCode
import vim
from pathlib import Path
from pydantic import BaseModel, ConfigDict

from pytoy.ui.vscode.api import Api


class Uri(BaseModel):
    path: str
    scheme: str
    fsPath: str | None = None

    model_config = ConfigDict(extra="allow", frozen=True)

    def __eq__(self, other):
        if isinstance(other, Uri):
            if self.scheme == "file":
                return (self._norm_filepath(self.path), self.scheme) == (
                    self._norm_filepath(other.path),
                    other.scheme,
                )
            else:
                return (self.path, self.scheme) == (other.path, other.scheme)
        return False

    def __hash__(self):
        if self.scheme == "file":
            return hash((self._norm_filepath(self.path), self.scheme))
        else:
            return hash((self.path, self.scheme))

    def _norm_filepath(self, filepath: str) -> str:
        return Path(filepath.strip("/")).resolve().as_posix()


class Document(BaseModel):
    uri: Uri
    model_config = ConfigDict(extra="allow")

    @classmethod
    def get_current(cls):
        api = Api()
        doc = api.eval_with_return(
            "vscode.window.activeTextEditor.document", with_await=False
        )
        return Document(**doc)

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

    def append(self, text: str):
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
            args={"args": {"path": self.uri.path, "text": f"{text}"}},
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
            args={
                "args": {
                    "path": self.uri.path,
                }
            },
        )
        return result

    @content.setter
    def content(self, value):
        api = Api()
        js_code = """
        (async (path, content) => {
      const doc = vscode.workspace.textDocuments.find(
        d => d.uri.path === path
      );

      if (!doc) {
        return false;
      }

      const editors = vscode.window.visibleTextEditors.filter(e => e.document === doc);
      if (editors.length == 0) {
        return false;
      }
      const editor = editors[0];

      await editor.edit(editBuilder => {
          const fullRange = new vscode.Range(
              doc.positionAt(0),
              doc.positionAt(doc.getText().length)
          );
          editBuilder.delete(fullRange);
          editBuilder.insert(new vscode.Position(0, 0), content);
      });
    })(args.path, args.value)
    """
        result = api.eval_with_return(
            js_code,
            with_await=True,
            args={"args": {"path": self.uri.path, "value": value}},
        )
        return result

    def show(self, with_focus: bool = False):
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

        result = api.eval_with_return(js_code, with_await=True, args=args)
        return result

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Document):
            return NotImplemented
        return self.uri == other.uri


def get_uris() -> list[Uri]:
    """Return the `fsPaths`."""
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
    """Delete `untitle` documents without warning."""
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


class BufferURISolver:
    @classmethod
    def _to_uri(cls, buf_name: str):
        path = Path(buf_name)
        if path.name.startswith("untitled:"):
            scheme = "untitled"
            path = Path(path).name.strip(f"{scheme}:")
            fsPath = path
            return Uri(path=path, scheme=scheme, fsPath=fsPath)
        else:
            scheme = "file"
            path = path.resolve().as_posix()
            fsPath = path
            return Uri(path=path, scheme=scheme, fsPath=fsPath)

    @classmethod
    def _to_key(cls, uri: Uri):
        if uri.scheme == "file":
            return (uri.scheme, Path(uri.fsPath))
        elif uri.scheme == "untitled":
            return (uri.scheme, uri.path)
        else:
            return (uri.scheme, uri.path)

    @classmethod
    def get_bufnr_to_uris(cls) -> dict:
        number_to_uri = {buf.number: cls._to_uri(buf.name) for buf in vim.buffers}
        key_to_number = {
            cls._to_key(uri): number for number, uri in number_to_uri.items()
        }
        key_to_uri = {cls._to_key(uri): uri for uri in get_uris()}

        keys = key_to_number.keys() & key_to_uri.keys()
        result = {key_to_number[key]: key_to_uri[key] for key in keys}
        return result

    @classmethod
    def get_uri_to_bufnr(cls) -> dict[Uri, int]:
        # [NOTE]: This class is not throughly checked.
        return {cls._to_uri(buf.name): buf.number for buf in vim.buffers}

    @classmethod
    def get_bufnr(cls, uri: Uri) -> int | None:
        number_to_uri = {buf.number: cls._to_uri(buf.name) for buf in vim.buffers}
        key_to_number = {
            cls._to_key(uri): int(number) for number, uri in number_to_uri.items()
        }
        uri_key = cls._to_key(uri)
        return key_to_number.get(uri_key)

    @classmethod
    def get_uri(cls, bufnr: int) -> Uri | None:
        # [NOTE]: This may unstready, esps. `cls._to_key`'s construction
        # If the behavior is not expected, it may be a good idea to use `get_urls`
        # and `true` `URI`.
        number_to_uri = {buf.number: cls._to_uri(buf.name) for buf in vim.buffers}
        return number_to_uri.get(bufnr)
