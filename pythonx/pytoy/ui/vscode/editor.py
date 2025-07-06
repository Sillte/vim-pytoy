from pytoy.ui.vscode.document import Api, Uri, Document
from pytoy.ui.vscode.document import BufferURISolver, Uri
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

