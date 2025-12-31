from pytoy.ui.vscode.document import Api, Uri, Document
from pytoy.ui.vscode.buffer_uri_solver import BufferURISolver
from pydantic import BaseModel, ConfigDict, ValidationError, Field, PrivateAttr
from typing import Sequence, Self, Literal

from pytoy.ui.vscode.editor.models import TextEditorRevealType


class Editor(BaseModel):
    document: Document
    viewColumn: int | None = None
    model_config = ConfigDict(extra="allow", frozen=True)

    def _update_document(self, doc: Document) -> None:
        object.__setattr__(self, "document", doc)

    @staticmethod
    def get_current() -> "Editor":
        api = Api()
        data = api.eval_with_return("vscode.window.activeTextEditor", with_await=False)
        return Editor.model_validate(data)

    @staticmethod
    def get_editors() -> Sequence["Editor"]:
        # As of 2025/11, there is no API to get non-visible editors in vscode.
        api = Api()
        data_list = api.eval_with_return(
            "vscode.window.visibleTextEditors", with_await=False
        )
        return [Editor.model_validate(data) for data in data_list]

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
        try:
            pairs = [(Uri.model_validate(pair[0]), pair[1]) for pair in pairs]
        except ValidationError:
            return False

        uris = set(BufferURISolver.get_uri_to_bufnr().keys())
        uri_to_views = {pair[0]: pair[1] for pair in pairs if pair[0] in uris}
        return uri_to_views.get(self.uri, -1) == self.viewColumn

    @classmethod
    def create(cls, uri: Uri, split_mode: Literal["vertical", "horizontal"] = "vertical", cursor: tuple[int, int] | None = None) -> Self:
        jscode = """
        (async (args) => {
            const uri = vscode.Uri.parse(args.uriKey);
            const doc = await vscode.workspace.openTextDocument(uri);
            let options = {
                preview: false
            };
            if (args.cursor) {
                const pos = new vscode.Position(args.cursor[0], args.cursor[1]);
                options.selection = new vscode.Range(pos, pos);
            }

            let editor;
            if (!args.splitMode.startsWith("v")){
                await vscode.commands.executeCommand("workbench.action.splitEditorDown");
                editor = await vscode.window.showTextDocument(doc, options);
            }
            else {
                options.viewColumn = vscode.ViewColumn.Beside;
                editor = await vscode.window.showTextDocument(doc, options);
            }

            await new Promise(resolve => setTimeout(resolve, 0));
            if (!editor.viewColumn){
                await new Promise(resolve => setTimeout(resolve, 50));
            }
            if (!editor.viewColumn){
                throw new Error("viewColumn not assigned in time");
            }
            return [doc, editor.viewColumn]
        })(args)
        """
        api = Api()
        opts = {"args": {"uriKey": uri.to_key_str(), "splitMode": split_mode, "cursor": cursor}}
        doc_dict, view_column = api.eval_with_return(jscode, opts)
        return cls.model_validate({"document":doc_dict, "viewColumn":view_column})

    def show(
        self,
        uri: Uri,
        position: tuple[int , int] | None = None,
        preview: bool = False
    ) -> "Editor":
        """Open the document specified by `uri`."""

        jscode = """
        (async ({ uriKey, viewColumn, preview, line, col }) => {
            const uri = vscode.Uri.parse(uriKey);
            const doc = await vscode.workspace.openTextDocument(uri);

            const editor = await vscode.window.showTextDocument(doc, {
                viewColumn: viewColumn,
                preview: preview,
                preserveFocus: false
            });

            if (line !== undefined && col !== undefined) {
                const pos = new vscode.Position(line, col);
                editor.selection = new vscode.Selection(pos, pos);
                editor.revealRange(new vscode.Range(pos, pos), vscode.TextEditorRevealType.InCenter);
            }
            return doc
        })(args)
        """

        args = {
            "args": {
                "uriKey": uri.to_key_str(),
                "viewColumn": self.viewColumn,
                "preview": preview,
                "line": position[0] if position else None,
                "col": position[1] if position else None,
            }
        }

        api = Api()
        doc_data = api.eval_with_return(jscode, opts=args)

        # Update of state.
        doc = Document.model_validate(doc_data)
        self._update_document(doc)
        return Editor(document=doc, viewColumn=self.viewColumn)

    def close(self) -> bool:
        jscode = """
        (async (uriKey, viewColumn) => {
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
                              (editor.document.uri.authority || "") == (uri.authority  || "") && 
                              editor.viewColumn == viewColumn
                );
            }

            async function forceCloseEditorByUri(uriKey, column) {
                const uri = vscode.Uri.parse(uriKey);
                const editor = findEditorByUriAndColumn(uri, column);

                if (!editor) return false;

                await closeUntitledEditorSafely(editor);
                return true;
            }

            return forceCloseEditorByUri(uriKey, viewColumn)
        })(args.uriKey, args.viewColumn)
        """
        api = Api()

        args = {"args": {"uriKey": self.uri.to_key_str(), "viewColumn": self.viewColumn}}
        return api.eval_with_return(jscode, with_await=True, opts=args)

    def focus(self) -> None:
        jscode = """
        (async (uriKey, viewColumn) => {
            function findEditorByUriAndColumn(uri, viewColumn) {
                return vscode.window.visibleTextEditors.find(
                    editor => editor.document.uri.path == uri.path &&
                              editor.document.uri.scheme == uri.scheme && 
                              (editor.document.uri.authority || "") == (uri.authority  || "") && 
                              editor.viewColumn == viewColumn
                );
            }
            async function FocusEditor(uriKey, column) {
                const uri = vscode.Uri.parse(uriKey);
                const editor = findEditorByUriAndColumn(uri, column);
                if (!editor) return false;
                await vscode.window.showTextDocument(editor.document, {
                    viewColumn: editor.viewColumn,
                    preview: false
                });
                return true;
            }
            return FocusEditor(uriKey, viewColumn)
        })(args.uriKey, args.viewColumn)
        """
        api = Api()
        args = {"args": {"uriKey": self.uri.to_key_str(), "viewColumn": self.viewColumn}}
        return api.eval_with_return(jscode, with_await=True, opts=args)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Editor):
            return NotImplemented
        # [NOTE]: We have to be careful since viewColumn corresponds to the one
        # when this class is created.
        return (self.document == other.document) and (
            self.viewColumn == other.viewColumn
        )

    def get_clean_target_uris_for_unique(self, within_tabs: bool = False, within_windows: bool = True) -> Sequence[Uri]:
        from pytoy.ui.vscode.editor.clearners import EditorCleaner
        return EditorCleaner(self).get_clean_target_uris_for_unique(within_tabs=within_tabs,
                                                                     within_windows=within_windows)


    def unique(self, within_tabs: bool = False, within_windows: bool = True):
        from pytoy.ui.vscode.editor.clearners import EditorCleaner
        return EditorCleaner(self).unique(within_tabs=within_tabs,
                                          within_windows=within_windows)

    @property
    def cursor_position(self) -> tuple[int, int] | None:
        """Return the (lnum, lcol) of the editor.
        """
        jscode = """
        (async (args) => {
            function findEditorByUriAndColumn(uri, viewColumn) {
                return vscode.window.visibleTextEditors.find(
                    editor => editor.document.uri.path == uri.path &&
                              editor.document.uri.scheme == uri.scheme && 
                              (editor.document.uri.authority || "") == (uri.authority  || "") && 
                              editor.viewColumn == viewColumn
                );
            }
            const uri = vscode.Uri.parse(args.uriKey);
            const editor = findEditorByUriAndColumn(uri, args.viewColumn);

            if (!editor) return null;
            const pos = editor.selection.active;
            return [pos.line, pos.character];
        })(args)
        """
        args = {
            "args": {
                "uriKey": self.uri.to_key_str(),
                "viewColumn": self.viewColumn,
            }
        }
        api = Api()
        ret = api.eval_with_return(jscode, with_await=True, opts=args)
        if ret is None:
            return None
        return (ret[0], ret[1])

    def set_cursor_position(self, line: int , col: int, reveal_type: TextEditorRevealType = TextEditorRevealType.Default) -> bool:
        """Move the cursor to the position.
        """
        jscode = """
        (async (args) => {
            function findEditorByUriAndColumn(uri, viewColumn) {
                return vscode.window.visibleTextEditors.find(
                    editor => editor.document.uri.path == uri.path &&
                              editor.document.uri.scheme == uri.scheme &&
                              (editor.document.uri.authority || "") == (uri.authority || "") &&
                              editor.viewColumn == viewColumn
                );
            }

            const uri = vscode.Uri.parse(args.uriKey);
            const editor = findEditorByUriAndColumn(uri, args.viewColumn);
            if (!editor) return false;

            const position = new vscode.Position(args.line, args.col);
            editor.selection = new vscode.Selection(position, position);

            editor.revealRange(
                new vscode.Range(position, position),
                args.revealType
            );

            return true;
        })(args)
        """

        args = {
            "args": {
                "uriKey": self.uri.to_key_str(),
                "viewColumn": self.viewColumn,
                "line": line,
                "col": col,
                "revealType": int(reveal_type)
            }
        }
        api = Api()
        return api.eval_with_return(jscode, with_await=True, opts=args)