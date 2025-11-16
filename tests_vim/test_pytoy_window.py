import vim 
from pytoy.ui.pytoy_window import PytoyWindowProvider
from pytoy.ui.pytoy_window import PytoyWindow
from pytoy.ui.vscode.editor import Editor
from pytoy.ui.vscode.document import Uri
from pytoy.ui.vscode.api import Api

print(Uri.from_bufname(r"c:\LocalLibrary\PublicLibrary\vim-pytoy\search-editor:#0.8964251299312702"))

PytoyWindowProvider().create_window("hogehoge")
for window in PytoyWindow.get_windows():
    print(window.buffer.path)











