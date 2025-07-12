import vim

from pytoy.ui.vscode.api import Api
from pytoy.ui.vscode.document import BufferURISolver, Uri
from contextlib import contextmanager



def get_uri_to_views(only_displayed: bool = False, with_buffer: bool =True) -> dict[Uri, int | None]:
    """Return the pair of `Uri` of document and `int` as view number. 
    """
    jscode = """
    (async () => {
      const editors = vscode.window.visibleTextEditors;
      const pairs = editors.map((editor) => {
        const doc = editor.document;
        const viewCol = editor.viewColumn;
        return [doc.uri, viewCol];
      });
      return pairs;
    })()
    """
    api = Api()
    pairs = api.eval_with_return(jscode, with_await=True)
    pairs = [(Uri(**pair[0]), pair[1]) for pair in pairs]
    if only_displayed:  # In case of dispaly, `view` is not None.
        pairs = [pair for pair in pairs if pair[1]]

    uris = set(BufferURISolver.get_uri_to_bufnr().keys())
    uri_to_views = {pair[0]: pair[1] for pair in pairs}
    if with_buffer:
        uri_to_views = {key: value for key, value in uri_to_views.items() if key in uris}
    return uri_to_views


def get_active_viewcolumn() -> int | None:
    api = Api()
    try:
        active_column = api.eval_with_return(
            "vscode.window.activeTextEditor.viewColumn", with_await=False
        )
    except Exception as e:
        print(e)
        return None
    return active_column


def set_active_viewcolumn(viewcolumn: int):
    api = Api()
    jscode = """
    (async (column) => {
  function getEditorInColumn(column) {
    return vscode.window.visibleTextEditors.find(e => e.viewColumn === column);
  }

  async function focusEditor(editor) {
    await vscode.window.showTextDocument(editor.document,  {
      viewColumn: editor.viewColumn,
      preserveFocus: false,
      preview: false
    });
  }
  async function focusEditorByColumn(column) {
    const editor = getEditorInColumn(column);
    if (editor) {
      await focusEditor(editor);
    }
    else {
        await vscode.window.showInformationMessage('NOT Existing!');
    }
  }
      return await focusEditorByColumn(column);
    })(args.column)
    """
    args = {"args": {"column": int(viewcolumn)}}
    api.eval_with_return(jscode, with_await=True, args=args)


def get_active_uri() -> Uri | None:
    api = Api()
    try:
        uri = api.eval_with_return(
            "vscode.window.activeTextEditor.document.uri", with_await=False
        )
    except Exception as e:
        return None
    return Uri(**uri)


@contextmanager
def store_focus():
    viewcolumn = get_active_viewcolumn()
    uri = get_active_uri()

    def _revert_focus():
        if viewcolumn is not None:
            set_active_viewcolumn(viewcolumn)
        else:
            print("Viewcolumn is None.")
        if uri:
            bufnr = BufferURISolver.get_bufnr(uri)
            if bufnr is not None:
                vim.command(f"buffer {bufnr}")
            else:
                print("`bufnr` is not exist, so it fails to revert focus.")
        else:
            print("uri is None.")

    try:
        yield (viewcolumn, uri)
    except Exception as e:
        _revert_focus()
        raise e
    else:
        _revert_focus()


