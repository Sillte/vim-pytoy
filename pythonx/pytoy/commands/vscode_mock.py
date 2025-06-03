from pytoy.command import CommandManager

from pytoy.ui_pytoy.vscode.api import Api, Uri, Document, delete_untitles, get_uris

import vim


@CommandManager.register(name="VS")
def func():
    import pytoy
    import vim
    api = Api()
    ret = api.eval_with_return("vscode.window.activeTextEditor.document.fileName",
                               with_await=False)
    delete_untitles()
    print("uris", get_uris())
    from pathlib import Path
    path = [elem.path for elem in get_uris() if Path(elem.path).suffix == ".py"][0]
    print("path", path)
    doc = Document.from_path(path)
    u_doc = Document.create()
    u_doc.append("YAHH!!")
    ret = u_doc.show()
    print("showret", ret, u_doc.uri.path)
    print("uris", get_uris())
    u_doc.append("ABAC!!")
    u_doc.append("AFAERE!!")
    return 

 
