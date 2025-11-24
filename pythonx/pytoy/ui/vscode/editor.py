from pytoy.ui.vscode.document import Api, Uri, Document
from pytoy.ui.vscode.buffer_uri_solver import BufferURISolver
from pydantic import BaseModel, ConfigDict, ValidationError
from typing import Sequence, Self


class Editor(BaseModel):
    document: Document
    viewColumn: int | None = None
    model_config = ConfigDict(extra="allow", frozen=True)

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
    def create(cls, uri: Uri, split_mode: str = "vertical") -> Self:
        jscode = """
        (async (args) => {
            const uri = vscode.Uri.parse(args.uriKey);
            const doc = await vscode.workspace.openTextDocument(uri);

            let editor;
            if (args.splitMode.startsWith("v")){
                await vscode.commands.executeCommand("workbench.action.splitEditorDown");
                editor = await vscode.window.showTextDocument(doc, {
                    preview: false
                });
            }
            else {
                editor = await vscode.window.showTextDocument(doc, {
                viewColumn: vscode.ViewColumn.Beside, // 今開いているエディタの横
                preview: true,
            });
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
        opts = {"args": {"uriKey": uri.to_key_str(), "splitMode": split_mode}}
        doc_dict, view_column = api.eval_with_return(jscode, opts)
        return cls.model_validate({"document":doc_dict, "viewColumn":view_column})

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
        """Return the `dirty` uris which should be empty for the smooth `unique`.
        """
        jscode = """
        (async (args) => {
            
            /**
             * すべてのUntitledドキュメントを収集します。
             * @returns {vscode.TextDocument[]} 
             */
            function collectUntitled() {
                // vscodeはグローバルに存在すると仮定
                return vscode.workspace.textDocuments.filter(
                    doc => doc.uri.scheme === "untitled"
                );
            }

            /**
             * 削除対象から除外（キープ）すべきUntitledドキュメントのURIのSetを収集します。
             * @param {vscode.TextEditor} targetEditor 
             * @param {boolean} withinTab 
             * @param {boolean} withinWindows 
             * @returns {Set} URI文字列のSet
             */
            function collectUntitledToKeep(targetEditor, withinTab, withinWindows) {
                const targetColumn = targetEditor.viewColumn;

                const keep = new Set(); // JS構文に修正

                for (const group of vscode.window.tabGroups.all) {
                    const isSameGroup = group.viewColumn === targetColumn;

                    for (const tab of group.tabs) {
                        // tab.input が存在し、uriプロパティを持ち、schemeが"untitled"であるかチェック
                        // tab.input.uri が存在しない場合があるため、安全にアクセス
                        const uri = tab.input && tab.input.uri;
                        if (!uri || uri.scheme !== "untitled") continue;

                        const isTargetTab = uri.toString() === targetEditor.document.uri.toString();

                        // 削除ゾーンの条件:
                        // 1. (withinWindowsがtrue かつ ターゲットと同じグループではない)
                        // 2. または (withinTabがtrue かつ ターゲットと同じグループ かつ ターゲットのタブではない)
                        const inRemovalZone =
                            (args.withinWindows && !isSameGroup) ||
                            (args.withinTab && isSameGroup && !isTargetTab);

                        // 削除対象でない（キープすべき）場合、Setに追加
                        if (!inRemovalZone) {
                            keep.add(uri.toString());
                        }
                    }
                }
                return keep;
            }

            /**
             * クリーンアップ対象となるUntitledドキュメントのURIの配列を返します。
             * @param {vscode.TextEditor} targetEditor 
             * @param {boolean} withinTab 
             * @param {boolean} withinWindows 
             * @returns {any[]} URIのJSONオブジェクトの配列
             */
            function getCleanUntitledTargets(targetEditor, withinTab, withinWindows) {
                const dirty = collectUntitled();
                const keep = collectUntitledToKeep(targetEditor, withinTab, withinWindows);

                // クリーンアップ対象 (キープリストに含まれていないもの)
                const toCleanDocs = dirty.filter(doc => !keep.has(doc.uri.toString()));

                // URIオブジェクトの配列に変換して返却
                return toCleanDocs.map(doc => doc.uri.toJSON()); 
            }

            function findEditorByUriAndColumn(uri, viewColumn) {
                return vscode.window.visibleTextEditors.find(
                    editor => editor.document.uri.path == uri.path &&
                              editor.document.uri.scheme == uri.scheme && 
                              (editor.document.uri.authority || "") == (uri.authority  || "") && 
                              editor.viewColumn == viewColumn
                );
            }

            // --- メイン処理 ---
            
            // args.uri は Lua 側から渡されたディクショナリ形式（または文字列）を想定
            const targetUri = vscode.Uri.parse(args.uriKey);
            
            
            // ターゲットエディタを見つける
            const editor = findEditorByUriAndColumn(targetUri, args.viewColumn)

            if (!editor) return [];

            // クリーンアップ対象のURIリストを取得
            return getCleanUntitledTargets(editor, args.withinTab, args.withinWindows);

        })(args)
        """

        args = {
            "args": {
                "uriKey": self.uri.to_key_str(),
                "viewColumn": self.viewColumn,
                "withinTab": within_tabs,
                "withinWindows": within_windows,
            }
        }
        api = Api()
        if self.viewColumn is None:
            msg = "`viewColumn` must not be None in `unique`."
            raise ValueError(msg)
        result = api.eval_with_return(jscode, with_await=True, opts=args)
        return [Uri.model_validate(elem) for elem in result]

    def unique(self, within_tabs: bool = False, within_windows: bool = True):
        """Make it an unique editor."""
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

        // --- メイン処理 ---
        
        // args.uri は Lua 側から渡されたディクショナリ形式（または文字列）を想定
        const targetUri = vscode.Uri.parse(args.uriKey);
        
        // ターゲットエディタを見つける
        const editor = findEditorByUriAndColumn(targetUri, args.viewColumn)
        if (!editor) return; // ターゲットエディタが見つからなければ終了

        // ターゲットエディタを再度アクティブにしてフォーカスを維持
        await vscode.window.showTextDocument(editor.document, {
            viewColumn: args.viewColumn,
            preserveFocus: true
        });

        // withinTabがtrueの場合、同じグループ内の他のエディタを閉じる
        if (args.withinTab) {
            await vscode.commands.executeCommand(
                "workbench.action.closeOtherEditors"
            );
        }

        // withinWindowsがtrueの場合、他のグループのエディタを閉じる
        if (args.withinWindows) {
            await vscode.commands.executeCommand(
                "workbench.action.closeEditorsInOtherGroups"
            );
        }
    })(args);
    """
        args = {
            "args": {
                "uriKey": self.uri.to_key_str(), 
                "viewColumn": self.viewColumn,
                "withinTab": within_tabs,
                "withinWindows": within_windows,
            }
        }
        api = Api()
        if self.viewColumn is None:
            msg = "`viewColumn` must not be None in `unique`."
            raise ValueError(msg)
        return api.eval_with_return(jscode, with_await=True, opts=args)

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
            return [pos.line + 1, pos.character + 1];
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