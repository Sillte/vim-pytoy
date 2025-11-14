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
    function countAllDocumentInstances() {
        const uriToCount = new Map();
        for (const group of vscode.window.tabGroups.all) {
            for (const tab of group.tabs) {
                // tab.input がテキスト入力（ファイルまたは untitled）であることを確認
                if (tab.input && tab.input.uri) {
                    const uriStr = tab.input.uri.toString();
                    uriToCount.set(uriStr, (uriToCount.get(uriStr) || 0) + 1);
                }
            }
        }
        return uriToCount;
    }

    /**
     * 特定のエディタと同じグループにある、そのエディタ以外のすべてのタブを閉じます。
     * untitled ファイルについては、それがそのURIの最後のインスタンスである場合にのみ
     * 'revertAndCloseActiveEditor' を使用して閉じます。
     * * @param {vscode.TextEditor} editor - 基準となるエディタ
     * @param {Map<string, number>} uriToCount - 全ドキュメントのインスタンスカウント
     */
    async function revertCloseTabWithinEditor(editor, uriToCount) {
        const targetColumn = editor.viewColumn;
        const targetUriStr = editor.document.uri.toString();
        
        // ターゲット Group を特定
        const targetGroup = vscode.window.tabGroups.all.find(
            g => g.viewColumn === targetColumn
        );
        if (!targetGroup) return;

        // 閉じる対象のタブを収集。元のエディタ（targetUriStr）は除く
        const tabsToClose = targetGroup.tabs.filter(tab => {
            return tab.input && tab.input.uri && tab.input.uri.toString() !== targetUriStr;
        });

        // 削除処理を実行
        for (const tab of tabsToClose) {
            const uri = tab.input.uri;
            const uriStr = uri.toString();
            const scheme = uri.scheme;
            
            let currentCount = uriToCount.get(uriStr) || 0;
            
            // 1. タブをアクティブ化（特定 column を維持）
            await vscode.window.showTextDocument(uri, {
                viewColumn: targetColumn,
                preview: true // "上書き可能タブ"として扱う
            });

            // このタブを閉じると、そのURIの開かれている数が1以下になるかどうか
            const isLastEditorForUri = currentCount <= 1;

            // 2. 削除処理を実行
            if (scheme === "untitled" && isLastEditorForUri) {
                 // 最後の untitled インスタンスの場合: revertAndClose
                await vscode.commands.executeCommand("workbench.action.revertAndCloseActiveEditor");
            } else {
                // 通常のファイル、または他の場所でも開かれている untitled の場合: close
                await vscode.commands.executeCommand("workbench.action.closeActiveEditor");
            }
            
            // 3. 辞書のカウントをデクリメント
            if (currentCount > 0) {
                uriToCount.set(uriStr, currentCount - 1);
            }
        }
        
        // 最後に “元の editor” にフォーカスを戻して安定状態に戻す
        await vscode.window.showTextDocument(editor.document, {
            viewColumn: editor.viewColumn, // アクティブエディタのviewColumnに戻す
            preview: false // 固定タブとして開く
        });
    }

    /**
     * ターゲットエディタが開かれているグループ以外の、全てのタブを閉じます。
     *
     * @param {vscode.TextEditor} targetEditor - 残したいエディタグループを特定するための基準エディタ
     * @param {Map<string, number>} uriToCount - 全ドキュメントのインスタンスカウント
     */
    async function closeOtherWindows(targetEditor, uriToCount) {
        const targetColumn = targetEditor.viewColumn;

        // ターゲットグループ以外の閉じる対象タブを収集
        const tabsToClose = [];

        for (const group of vscode.window.tabGroups.all) {
            if (group.viewColumn === targetColumn) continue; // ターゲットグループはスキップ

            for (const tab of group.tabs) {
                const input = tab.input;
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
        
        // viewColumn の降順で sort（右→左で閉じることで安定性を高める）
        tabsToClose.sort((a, b) => (b.viewColumn || 0) - (a.viewColumn || 0));

        // 安定した順で閉じる
        for (const tab of tabsToClose) {
            const uriStr = tab.uri.toString();
            let currentCount = uriToCount.get(uriStr) || 0;

            // 1. タブをアクティブ化
            await vscode.window.showTextDocument(tab.uri, {
                preview: true,
                viewColumn: tab.viewColumn // 閉じる対象のグループでアクティブ化
            });

            // このタブを閉じると、そのURIの開かれている数が1以下になるかどうか
            const isLastEditorForUri = currentCount <= 1;

            // 2. 削除処理を実行
            if (tab.scheme === "untitled" && isLastEditorForUri) {
                await vscode.commands.executeCommand("workbench.action.revertAndCloseActiveEditor");
            } else {
                await vscode.commands.executeCommand("workbench.action.closeActiveEditor");
            }

            // 3. 辞書のカウントをデクリメント
            if (currentCount > 0) {
                uriToCount.set(uriStr, currentCount - 1);
            }
        }
    }

// --- メイン実行ロジック (元のコードの IIFE 部分を関数にまとめたもの) ---

/**
 * 外部から受け取った引数に基づき、タブを閉じる操作を実行します。
 * @param {object} args - 実行に必要な引数
 */
async function executeCloseOperations(args) {
    // 必須引数のチェック
    if (!args || !args.uri || !args.viewColumn) return;

    const uri_dict = args.uri;
    const viewColumn = args.viewColumn;
    const withinTab = args.withinTab;
    const withinWindows = args.withinWindows;

    // 必要なエディタインスタンスを特定（元のコードの findEditorByUriAndColumn の代替）
    // vscode.window.activeTextEditorを信頼する代わりに、tabs APIを使ってターゲットエディタを特定する方が堅牢ですが、
    // ここでは便宜上、元のコードの意図通りにアクティブなエディタリストから探します。
    const uri = vscode.Uri.from({ "scheme": uri_dict.scheme, "path": uri_dict.path });
    const editor = vscode.window.visibleTextEditors.find(
        editor => editor.document.uri.toString() === uri.toString() &&
                  editor.viewColumn === viewColumn
    );

    // 両方の操作で必要となるため、一度だけURIカウントマップを作成
    const uriToCount = countAllDocumentInstances(vscode);
    
    // closeOtherWindows (他のグループを閉じる) を先に実行
    if (withinWindows) {
        await closeOtherWindows(editor, uriToCount);
    }
    
    // revertCloseTabWithinEditor (現在のグループの他のタブを閉じる) を実行
    if (withinTab) {
        await revertCloseTabWithinEditor(editor, uriToCount);
    }
}
    await executeCloseOperations(args)
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
