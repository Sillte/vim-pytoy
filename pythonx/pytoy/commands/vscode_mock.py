from pytoy.shared.command import App
from pytoy.shared.lib.backend import get_backend_enum, BackendEnum
from pytoy.shared.ui.utils import to_filepath

app = App()


#@app.command(name="Source")
# TODO: It is required to think about specification of Argument`.
#def source(fargs: list[str]):
#    import vim
#    vals = [vim.eval(f'expand("{elem}")') for elem in opts.fargs]
#    vals = [to_filepath(elem) for elem in vals]
#    vim.command(f'source {" ".join(map(str, vals))}') 


@app.command(name="MyWindow")
def mywindow_func2():
    from pytoy.shared.ui.pytoy_window import PytoyWindowProvider
    # window = PytoyWindow.get_current()
    # PytoyWindowProvider().create_window("hgoehoge", "s")
    # print(window.buffer)
    # print(window.buffer.content)
    # window.focus()
    from pytoy.job_execution.utils import get_current_directory

    Api().eval_with_return("vscode.env.remoteName") 
    print("GETCURRENT", get_current_directory())
    return

    from pytoy.shared.ui.pytoy_window.impl_vscode import (
        PytoyBufferVSCode,
    )
    PytoyBufferVSCode

    windows = PytoyWindowProvider().get_windows()
    for elem in windows:
        print(elem.buffer._impl.document)
    for elem in PytoyWindowProvider().get_windows():
        print(elem.buffer._impl.document.uri.path)


@app.command(name="IsRemote")
def mywindow_func():
    print("hgoegege")
    from pytoy.shared.ui.pytoy_window import PytoyWindowProvider
    # window = PytoyWindow.get_current()
    # PytoyWindowProvider().create_window("hgoehoge", "s")
    # print(window.buffer)
    # print(window.buffer.content)
    # window.focus()

    from pytoy.shared.ui.pytoy_window.impls.vscode import (
        PytoyBufferVSCode,
    )

    windows = PytoyWindowProvider().get_windows()
    for elem in windows:
        print(elem.buffer._impl.uri)  #type: ignore
    for elem in PytoyWindowProvider().get_windows():
        print(elem.buffer._impl.uri.path) #type: ignore

    # windows[0].impl.editor.focus()
    # print(window.valid, window.impl.editor.document.uri)
    # window.buffer
    # window.unique()



if get_backend_enum() == BackendEnum.VSCODE:
    from pytoy.shared.ui.vscode.api import Api
    from pytoy.shared.ui.vscode.editor import Editor

    def script():
        jscode = """
        (async () => {
        return vscode.commands.getCommnds(true)
        //await vscode.commands.executeCommand('workbench.action.focusNextGroup');
        //const sleep = (time) => new Promise((resolve) => setTimeout(resolve, time));
        //await sleep(10)
        })()
        """
        return jscode

    @app.command(name="MOCK")
    def mock_function():
        # api = Api()
        # data = api.eval_with_return("vscode.window.activeTextEditor", with_await=False)
        # pprint(data)
        print(Editor.get_current())
        for elem in Editor.get_editors():
            print(elem)

        # editor = Editor.get_current()
        # print("result", editor.close())
        # return
        # scheme = "untitled"

        # uri = Uri(path=TERM_STDOUT, scheme="untitled")
        # uri_to_views = get_uri_to_views()
        # if uri in uri_to_views:
        #    doc = Document(uri=uri)
        # else:
        #   pass

    @app.command(name="MOCKA")
    def __call__():
        api = Api()
        commands = api.eval_with_return(
            "vscode.commands.executeCommand('github.copilot.chat.explain');",
            with_await=True,
        )
        print(commands)