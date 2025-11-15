from pytoy.command import CommandManager, OptsArgument
from pytoy.ui import get_ui_enum, UIEnum


@CommandManager.register(name="MyWindow", range=True)
def mywindow_func():
    print("hgoegege")
    from pytoy.ui.pytoy_window import PytoyWindowProvider

    # window = PytoyWindow.get_current()
    # PytoyWindowProvider().create_window("hgoehoge", "s")
    # print(window.buffer)
    # print(window.buffer.content)
    # window.focus()
    from pytoy.lib_tools.utils import get_current_directory

    val = Api().eval_with_return("vscode.env.remoteName")
    print("GETCURRENT", get_current_directory())
    return

    from pytoy.ui.pytoy_window.impl_vscode import (
        PytoyBufferVSCode,
    )

    PytoyBufferVSCode

    windows = PytoyWindowProvider().get_windows()
    for elem in windows:
        print(elem.buffer._impl.document)
    for elem in PytoyWindowProvider().get_windows():
        print(elem.buffer._impl.document.uri.path)


@CommandManager.register(name="IsRemote")
def mywindow_func():
    print("hgoegege")
    from pytoy.ui.pytoy_window import PytoyWindowProvider
    # window = PytoyWindow.get_current()
    # PytoyWindowProvider().create_window("hgoehoge", "s")
    # print(window.buffer)
    # print(window.buffer.content)
    # window.focus()

    from pytoy.ui.pytoy_window.impl_vscode import (
        PytoyBufferVSCode,
    )

    PytoyBufferVSCode

    windows = PytoyWindowProvider().get_windows()
    for elem in windows:
        print(elem.buffer._impl.document)
    for elem in PytoyWindowProvider().get_windows():
        print(elem.buffer._impl.document.uri.path)

    # windows[0].impl.editor.focus()
    # print(window.valid, window.impl.editor.document.uri)
    # window.buffer
    # window.unique()


from pytoy.command import CommandManager


if get_ui_enum() == UIEnum.VSCODE:
    from pytoy.ui.vscode.api import Api
    from pytoy.ui.vscode.document import Api
    from pytoy.ui.vscode.editor import Editor

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

    @CommandManager.register(name="MOCK", range=True)
    class CommandFunctionClass1:
        def __call__(self, opts: OptsArgument):
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

    @CommandManager.register(name="MOCKA", range=True)
    class CommandFunctionClass:
        def __call__(self, opts: OptsArgument):
            api = Api()
            commands = api.eval_with_return(
                "vscode.commands.executeCommand('github.copilot.chat.explain');",
                with_await=True,
            )
            print(commands)
