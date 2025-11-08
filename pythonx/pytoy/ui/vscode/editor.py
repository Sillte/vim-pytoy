from pytoy.ui.vscode.document import Api, Uri, Document
from pytoy.ui.vscode.document import BufferURISolver
from pydantic import BaseModel, ConfigDict


class Editor(BaseModel):
    document: Document
    viewColumn: int | None = None
    model_config = ConfigDict(extra="allow", frozen=True)

    @staticmethod
    def get_current() -> "Editor":
        api = Api()
        data = api.eval_with_return("vscode.window.activeTextEditor", with_await=False)
        return Editor(**data)

    @staticmethod
    def get_editors() -> list["Editor"]:
        api = Api()
        data_list = api.eval_with_return(
            "vscode.window.visibleTextEditors", with_await=False
        )
        return [Editor(**data) for data in data_list]

    @property
    def uri(self) -> Uri:
        return self.document.uri

    @property
    def valid(self) -> bool:
        jscode = """
        (async () => {
          const editors = vscode.window.visibleTextEditors;
          const pairs = editors.map((editor) => {
            return [editor.document.uri, editor.viewColumn];
          });
          return pairs;
        })()
        """
        api = Api()
        pairs = api.eval_with_return(jscode, with_await=True)
        pairs = [(Uri(**pair[0]), pair[1]) for pair in pairs]

        uris = set(BufferURISolver.get_uri_to_bufnr().keys())
        uri_to_views = {pair[0]: pair[1] for pair in pairs if pair[0] in uris}
        return uri_to_views.get(self.uri, -1) == self.viewColumn

    def close(self) -> bool:
        jscode = """
        (async (uri_dict, viewColumn) => {
            async function closeUntitledEditorSafely(editor) {
                const current = vscode.window.activeTextEditor;

                if (editor !== current) {
                    await vscode.window.showTextDocument(editor.document, editor.viewColumn, false);
                }

                const doc = editor.document;

                if (doc.isUntitled && doc.isDirty) {
                    await vscode.commands.executeCommand('workbench.action.revertAndCloseActiveEditor');
                } else {
                    await vscode.commands.executeCommand('workbench.action.closeActiveEditor');
                }

                if (current && editor !== current) {
                    await vscode.window.showTextDocument(current.document, current.viewColumn, false);
                }
            }

            function findEditorByUriAndColumn(uri, viewColumn) {
                return vscode.window.visibleTextEditors.find(
                    editor => editor.document.uri.path == uri.path &&
                              editor.document.uri.scheme == uri.scheme && 
                              editor.viewColumn == viewColumn
                );
            }

            async function forceCloseEditorByUri(uri_dict, column) {
                const uri = vscode.Uri.from({"scheme": uri_dict.scheme, "path": uri_dict.path})
                const editor = findEditorByUriAndColumn(uri, column);

                if (!editor) return false;

                await closeUntitledEditorSafely(editor);
                return true;
            }

            return forceCloseEditorByUri(uri_dict, viewColumn)
        })(args.uri, args.viewColumn)
        """
        api = Api()

        args = {"args": {"uri": dict(self.uri), "viewColumn": self.viewColumn}}
        # [NOTE]: return of `True` or `False` must be considered.
        return api.eval_with_return(jscode, with_await=True, args=args)

    def focus(self):
        jscode = """
        (async (uri_dict, viewColumn) => {
            function findEditorByUriAndColumn(uri, viewColumn) {
                return vscode.window.visibleTextEditors.find(
                    editor => editor.document.uri.path == uri.path &&
                              editor.document.uri.scheme == uri.scheme && 
                              editor.viewColumn == viewColumn
                );
            }
            async function FocusEditor(uri_dict, column) {
                const uri = vscode.Uri.from({"scheme": uri_dict.scheme, "path": uri_dict.path})
                const editor = findEditorByUriAndColumn(uri, column);
                if (!editor) return false;
                await vscode.window.showTextDocument(editor.document, editor.viewColumn);
                return true;
            }
            return FocusEditor(uri_dict, viewColumn)
        })(args.uri, args.viewColumn)
        """
        api = Api()
        args = {"args": {"uri": dict(self.uri), "viewColumn": self.viewColumn}}
        return api.eval_with_return(jscode, with_await=True, args=args)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Editor):
            return NotImplemented
        # [NOTE]: We have to be careful since viewColumn corresponds to the one
        # when this class is created.
        return (self.document == other.document) and (
            self.viewColumn == other.viewColumn
        )

    def unique(self, within_tab: bool = False):
        """Make it an unique editor."""
        jscode = """
        (async (uri_dict, viewColumn, withinTab) => {
            function findEditorByUriAndColumn(uri, viewColumn) {
                return vscode.window.visibleTextEditors.find(
                    editor => editor.document.uri.path == uri.path &&
                              editor.document.uri.scheme == uri.scheme && 
                              editor.viewColumn == viewColumn
                );
            }
            
            async function revertCloseExcept(editor, withinTab) {

              for (const group of vscode.window.tabGroups.all) {
                if (!withinTab && group.viewColumn === editor.viewColumn) continue;
                for (const tab of group.tabs) {
                  const uri = tab.input?.uri?.toString();
                    if (!uri) continue;
                    if (uri  == editor.document.uri.toString()) {
                        if (group.viewColumn === editor.viewColumn){
                            continue;
                        } 
                        await vscode.window.showTextDocument(tab.input.uri, { preview: false });
                        await vscode.commands.executeCommand('workbench.action.closeActiveEditor')
                    }
                    else{
                        await vscode.window.showTextDocument(tab.input.uri, { preview: false });
                        await vscode.commands.executeCommand('workbench.action.revertAndCloseActiveEditor');
                    }
                }
             }
           }
            const uri = vscode.Uri.from({"scheme": uri_dict.scheme, "path": uri_dict.path})
            const editor = findEditorByUriAndColumn(uri, viewColumn);
            await revertCloseExcept(editor, withinTab)
            if (!withinTab) {
              await vscode.commands.executeCommand('workbench.action.closeEditorsInOtherGroups');
            }

        })(args.uri, args.viewColumn, args.withinTab)
        """
        args = {
            "args": {
                "uri": dict(self.uri),
                "viewColumn": self.viewColumn,
                "withinTab": within_tab,
            }
        }
        api = Api()

        return api.eval_with_return(jscode, with_await=True, args=args)
