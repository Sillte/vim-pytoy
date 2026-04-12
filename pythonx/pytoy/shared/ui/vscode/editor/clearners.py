from pytoy.shared.ui.vscode.document import Api, VSCodeUri
from typing import Sequence

from pytoy.shared.ui.vscode.editor import Editor

class EditorCleaner:
    def __init__(self, editor: Editor):
        self._editor = editor

    @property
    def editor(self) -> Editor:
        return self._editor

    def get_clean_target_uris_for_unique(self, within_tabs: bool = False, within_windows: bool = True) -> Sequence[VSCodeUri]:
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
        return [VSCodeUri.model_validate(elem) for elem in result]

    def unique(self, within_tabs: bool = False, within_windows: bool = True):
        """Make it an unique editor."""
        jscode = """
        (async (args) => {

            // -----------------------------
            // util
            // -----------------------------
            function sameUri(a, b) {
                return a.path === b.path &&
                       a.scheme === b.scheme &&
                       (a.authority || "") === (b.authority || "");
            }

            function findEditorByUriAndColumn(uri, viewColumn) {
                return vscode.window.visibleTextEditors.find(
                    editor =>
                        sameUri(editor.document.uri, uri) &&
                        editor.viewColumn === viewColumn
                );
            }

            async function activateEditor(doc, column) {
                return vscode.window.showTextDocument(doc, {
                    viewColumn: column,
                    preserveFocus: false,
                    preview: false, 
                });
            }

            // -----------------------------
            // ① clean untitled
            // -----------------------------
            async function cleanUntitledUris(uris) {

                for (const uri of uris) {
                    const doc = await vscode.workspace.openTextDocument(uri);

                    if (doc.isDirty) {
                        const tab = vscode.window.tabGroups.all
                          .flatMap(g => g.tabs)
                          .find(t => sameUri(t.input?.uri, uri));
                        const column = tab?.group?.viewColumn ?? null;

                        await vscode.window.showTextDocument(doc, {
                            preserveFocus: false, 
                            preview: true, 
                            viewColumn: column
                        });
                        await vscode.commands.executeCommand(
                            "workbench.action.revertAndCloseActiveEditor"
                        );
                    }
                }
            }

            // -----------------------------
            // main
            // -----------------------------
            const targetUri = vscode.Uri.parse(args.uriKey);
            const cleanTargets = args.cleanTargets.map(elem => vscode.Uri.parse(elem));

            const targetEditor = findEditorByUriAndColumn(
                targetUri,
                args.viewColumn
            );

            if (!targetEditor) return;

            const savedCursor = {
                line: targetEditor.selection.active.line,
                col: targetEditor.selection.active.character
            };

            // --- ① 先にuntitled掃除 ---
            if (cleanTargets && cleanTargets.length > 0) {
                await cleanUntitledUris(cleanTargets);
            }

            // --- ② targetを安定化 ---
            const editor = await activateEditor(
                targetEditor.document,
                args.viewColumn,
            );

            // --- ③ close処理 ---
            if (args.withinTab) {
                await vscode.commands.executeCommand(
                    "workbench.action.closeOtherEditors"
                );
            }

            if (args.withinWindows) {
                await vscode.commands.executeCommand(
                    "workbench.action.closeEditorsInOtherGroups"
                );
            }
            

            const finalDoc = await vscode.workspace.openTextDocument(targetUri);
            await vscode.window.showTextDocument(finalDoc, {
                preserveFocus: false,
                preview: false
            });
            

        })(args);
    """
        editor = self.editor
        clean_targets = self.get_clean_target_uris_for_unique(within_tabs=within_tabs, within_windows=within_windows)
        args = {
            "args": {
                "uriKey": editor.uri.to_key_str(), 
                "viewColumn": editor.viewColumn,
                "withinTab": within_tabs,
                "withinWindows": within_windows,
                "cleanTargets": [vscode_uri.to_key_str() for vscode_uri in clean_targets],
            }
        }
        api = Api()
        if editor.viewColumn is None:
            msg = "`viewColumn` must not be None in `unique`."
            raise ValueError(msg)
        return api.eval_with_return(jscode, with_await=True, opts=args)

    def deduplicate(self, only_visible: bool = False) -> None:
        """This function may have problems, but it seems to work in minimum level.
        `only_visible` is for the case that you want to close only visible ones or close all the `editors` inside hidden `tabs`.
        """
        jscode = """
        (async (args) => {

            function sameUri(a, b) {
                return a.path === b.path &&
                       a.scheme === b.scheme &&
                       (a.authority || "") === (b.authority || "");
            }

            function findVisibleEditorByUriAndColumn(uri, column) {
                return vscode.window.visibleTextEditors.find(
                    ed =>
                        ed.viewColumn === column &&
                        sameUri(ed.document.uri, uri)
                );
            }

            function findKeysByUri(uri) {
                const result = [];
                for (const group of vscode.window.tabGroups.all) {
                    for (const tab of group.tabs) {
                        const input = tab.input;
                        if (!input || !input.uri) continue;

                        if (sameUri(input.uri, uri)) {
                            result.push({
                                uri: input.uri,
                                column: tab.group.viewColumn
                            });
                        }
                    }
                }
                return result;
            }
            
            function calibrateSelfEditor(uri, fallbackColumn){
                const currentEditor = vscode.window.activeTextEditor;
                if (currentEditor && sameUri(currentEditor.document.uri, uri)) {
                    return currentEditor;
                }
                return findVisibleEditorByUriAndColumn(uri, fallbackColumn);
            }
            
            const currentEditor = vscode.window.activeTextEditor;
            const targetUri = vscode.Uri.parse(args.uriKey);
            const selfEditor = calibrateSelfEditor(targetUri, args.viewColumn);
            if (!selfEditor) return;
            const onlyVisible = args.onlyVisible;

            // --- dedupe loop ---
            while (true) {

                let targets = findKeysByUri(targetUri);
                if (targets.length <= 1) break;

                const others = targets
                    .filter(t => (t.column !== selfEditor.viewColumn))
                    .sort((a, b) => b.column - a.column);

                if (!others) break;

                const victim = others[0];
                const editor = findVisibleEditorByUriAndColumn(victim.uri, victim.column);

                if (!editor && onlyVisible){
                    break;
                }
                
                const doc = await vscode.workspace.openTextDocument(victim.uri);
                await vscode.window.showTextDocument(doc, {
                    viewColumn: victim.column,
                    preserveFocus: false
                });

                await vscode.commands.executeCommand("workbench.action.closeActiveEditor");
            }

            // --- restore ---
            if (currentEditor && !currentEditor.document.isClosed) {
                await vscode.window.showTextDocument(currentEditor.document, {
                    viewColumn: currentEditor.viewColumn,
                    preview: false
                });
            }

        })(args)
        """

        api = Api()
        args = {
            "args": {
                "uriKey": self.editor.uri.to_key_str(),
                "viewColumn": self.editor.viewColumn,
                "onlyVisible": only_visible,
            }
        }
        api.eval_with_return(jscode, with_await=True, opts=args)