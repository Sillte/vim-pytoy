from pytoy.ui.vscode.document import Api, Uri
from typing import Sequence, Self

from pytoy.ui.vscode.editor import Editor

class EditorCleaner:
    def __init__(self, editor: Editor):
        self._editor = editor

    @property
    def editor(self) -> Editor:
        return self._editor

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

        editor = self.editor

        args = {
            "args": {
                "uriKey": editor.uri.to_key_str(),
                "viewColumn": editor.viewColumn,
                "withinTab": within_tabs,
                "withinWindows": within_windows,
            }
        }
        api = Api()
        if editor.viewColumn is None:
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
        editor = self.editor
        args = {
            "args": {
                "uriKey": editor.uri.to_key_str(), 
                "viewColumn": editor.viewColumn,
                "withinTab": within_tabs,
                "withinWindows": within_windows,
            }
        }
        api = Api()
        if editor.viewColumn is None:
            msg = "`viewColumn` must not be None in `unique`."
            raise ValueError(msg)
        return api.eval_with_return(jscode, with_await=True, opts=args)