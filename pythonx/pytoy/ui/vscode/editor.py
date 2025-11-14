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
                await vscode.window.showTextDocument(editor.document, {
                    viewColumn: editor.viewColumn,
                    preview: false
                });
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

    def unique(self, within_tab: bool = False, within_windows: bool = True):
        """Make it an unique editor."""
        jscode = """
        (async (uri_dict, viewColumn, withinTab, withinWindows) => {
            function findEditorByUriAndColumn(uri, viewColumn) {
                return vscode.window.visibleTextEditors.find(
                    editor => editor.document.uri.path == uri.path &&
                              editor.document.uri.scheme == uri.scheme && 
                              editor.viewColumn == viewColumn
                );
            }
            
    async function revertCloseTabWithinEditor(editor) {
        const current_editor = vscode.window.activeTextEditor; 
        
        const targetColumn = editor.viewColumn;
        const targetUriStr = editor.document.uri.toString();

        // 1. 全てのURIの開かれているエディタ数を事前にカウント（最適化）
        // Map<string (uri.toString()), number (count)>
        const uriToCount = new Map();

        for (const group of vscode.window.tabGroups.all) {
            for (const tab of group.tabs) {
                if (tab.input && tab.input.uri) {
                    const uriStr = tab.input.uri.toString();
                    uriToCount.set(uriStr, (uriToCount.get(uriStr) || 0) + 1);
                }
            }
        }

        // 2. ターゲット Group と閉じる対象タブの収集
        const targetGroup = vscode.window.tabGroups.all.find(
            g => g.viewColumn === targetColumn
        );
        if (!targetGroup) return;

        // 閉じる対象のタブを収集。元のエディタ（targetUriStr）は除く
        const tabsToClose = targetGroup.tabs.filter(tab => {
            return tab.input && tab.input.uri && tab.input.uri.toString() !== targetUriStr;
        });

        // 3. 並び順の安定化
        // VS Codeの tabs 配列は左→右なので、通常は逆順で閉じると安定しますが、
        // ここでは取得した tabsToClose を使って、左から順に処理します。
        // （元のコードのソートは不要と判断し、安定性を高めるためそのままの順序で処理します）

        // 4. 削除処理を実行
        for (const tab of tabsToClose) {
            const uri = tab.input.uri;
            const uriStr = uri.toString();
            const scheme = uri.scheme;
            
            let currentCount = uriToCount.get(uriStr) || 0;
            
            // 4-1. タブをアクティブ化（特定 column を維持）
            // アクティブ化しないと "workbench.action.closeActiveEditor" が正しく動作しない
            await vscode.window.showTextDocument(uri, {
                viewColumn: targetColumn,
                preview: true // "上書き可能タブ"として扱う
            });

            // このタブを閉じると、そのURIの開かれている数が1以下になるかどうか
            const isLastEditorForUri = currentCount <= 1;

            // 4-2. undo 可能ファイルかどうかで処理分岐
            if (scheme === "untitled" && isLastEditorForUri) {
                 // 最後の untitled インスタンスの場合: revertAndClose
                await vscode.commands.executeCommand("workbench.action.revertAndCloseActiveEditor");
            } else {
                // 通常のファイル、または他の場所でも開かれている untitled の場合: close
                await vscode.commands.executeCommand("workbench.action.closeActiveEditor");
            }
            
            // 4-3. 辞書のカウントをデクリメント
            // 閉じたので総数を1減らす
            if (currentCount > 0) {
                uriToCount.set(uriStr, currentCount - 1);
            }
        }
        // 5. 最後に “元の editor” にフォーカスを戻して安定状態に戻す
        await vscode.window.showTextDocument(current_editor.document, {
            viewColumn: current_editor.viewColumn,
            preview: false // 固定タブとして開く
        });
        }

    async function closeOtherWindows(targetEditor) {
        const vscode = require('vscode');

        const targetColumn = targetEditor.viewColumn;

        // 1. 全てのURIの開かれているエディタ数を事前にカウント（最適化）
        // Map<string (uri.toString()), number (count)>
        const uriToCount = new Map();

        for (const group of vscode.window.tabGroups.all) {
            for (const tab of group.tabs) {
                // tab.input がテキスト入力であることを確認
                if (tab.input && tab.input.uri) {
                    const uriStr = tab.input.uri.toString();
                    uriToCount.set(uriStr, (uriToCount.get(uriStr) || 0) + 1);
                }
            }
        }

        // 2. ターゲットグループ以外の閉じる対象タブを収集
        const tabsToClose = [];

        for (const group of vscode.window.tabGroups.all) {
            // ターゲットグループはスキップ
            if (group.viewColumn === targetColumn) continue;

            for (const tab of group.tabs) {
                const input = tab.input;
                // TabInputTextのURIを持つタブのみを対象とする
                if (input && input.uri) {
                    const uri = input.uri;
                    tabsToClose.push({
                        uri: uri,
                        viewColumn: group.viewColumn,
                        scheme: uri.scheme
                    });
                }
            }
        }
        
        // 3. viewColumn の降順で sort（右→左で閉じることで安定性を高める）
        tabsToClose.sort((a, b) => (b.viewColumn || 0) - (a.viewColumn || 0));

        // 4. 安定した順で閉じる
        for (const tab of tabsToClose) {
            const uriStr = tab.uri.toString();
            let currentCount = uriToCount.get(uriStr) || 0;

            // 4-1. タブをアクティブ化
            // 閉じる対象のグループ（tab.viewColumn）でアクティブ化
            await vscode.window.showTextDocument(tab.uri, {
                preview: true,
                viewColumn: tab.viewColumn
            });

            // このタブを閉じると、そのURIの開かれている数が1以下になるかどうか
            const isLastEditorForUri = currentCount <= 1;

            // 4-2. 削除処理を実行
            if (tab.scheme === "untitled" && isLastEditorForUri) {
                // 最後の untitled インスタンスの場合: revertAndClose
                await vscode.commands.executeCommand("workbench.action.revertAndCloseActiveEditor");
            } else {
                // 通常のファイル、または他の場所でも開かれている untitled の場合: close
                await vscode.commands.executeCommand("workbench.action.closeActiveEditor");
            }

            // 4-3. 辞書のカウントをデクリメント
            // 閉じたので総数を1減らす
            if (currentCount > 0) {
                uriToCount.set(uriStr, currentCount - 1);
            }
        }
    }


        const uri = vscode.Uri.from({"scheme": uri_dict.scheme, "path": uri_dict.path})
        const editor = findEditorByUriAndColumn(uri, viewColumn);
        if (withinWindows) {
          await closeOtherWindows(editor)
        }
        if (withinTab){
            await revertCloseTabWithinEditor(editor)
        }

    })(args.uri, args.viewColumn, args.withinTab, args.withinWindows)
    """
        args = {
            "args": {
                "uri": dict(self.uri),
                "viewColumn": self.viewColumn,
                "withinTab": within_tab,
                "withinWindows": within_windows,
            }
        }
        api = Api()

        return api.eval_with_return(jscode, with_await=True, args=args)
