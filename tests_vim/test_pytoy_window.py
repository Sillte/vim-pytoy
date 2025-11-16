


def test_function():
    from pytoy.ui.pytoy_window import PytoyWindowProvider
    from pytoy.ui.pytoy_window import PytoyWindow
    from pytoy.ui.vscode.editor import Editor
    from pytoy.ui.vscode.document import Uri
    from pytoy.ui.vscode.api import Api
    
    target = "test_window"
    window = PytoyWindowProvider().create_window(target)
    assert window.buffer.path.name == target
    import time
    paths = [window.buffer.path for window in PytoyWindow.get_windows()]
    assert any(path.name == target for path in paths)
    

def test_unique():
    from pytoy.ui.pytoy_window import PytoyWindowProvider
    from pytoy.ui.pytoy_window import PytoyWindow
    from pytoy.ui.vscode.editor import Editor
    from pytoy.ui.vscode.document import Uri
    from pytoy.ui.vscode.api import Api
    
    current = PytoyWindow.get_current()
    current.unique(within_tabs=True, within_windows=False)
    

from pytoy.ui.pytoy_window import PytoyWindow
#test_function()
test_unique()
print("OK")
