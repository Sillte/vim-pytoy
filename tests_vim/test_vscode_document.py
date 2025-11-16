from pathlib import Path
from pytoy.ui.vscode.document import Uri
from pytoy.ui.vscode.api import Api

uri = Uri.from_bufname(r"c:\LocalLibrary\PublicLibrary\vim-pytoy\search-editor:#0.8964251299312702")
assert uri.scheme == "search-editor"

uri = Uri.from_bufname(r"c:\LocalLibrary\PublicLibrary\vim-pytoy\tests_vim\test_pytoy_window.py")
assert uri.scheme == "file", (uri)
assert Path(uri.path) == Path(r"c:\LocalLibrary\PublicLibrary\vim-pytoy\tests_vim\test_pytoy_window.py")

uri = Uri.from_bufname(r"c:\LocalLibrary\PublicLibrary\vim-pytoy\output:asvetliakov.vscode-neovim.vscode-neovim%20logs")

assert uri.scheme == "output", (uri.scheme, uri.path)
assert uri.path == "asvetliakov.vscode-neovim.vscode-neovim logs", (uri.path)

uri = Uri.from_bufname(r"c:\LocalLibrary\PublicLibrary\vim-pytoy\output:asvetliakov.vscode-neovim.vscode-neovim%20logs")

assert uri.scheme == "output", (uri.scheme, uri.path)
assert uri.path == "asvetliakov.vscode-neovim.vscode-neovim logs", (uri.path)

uri =  Uri.from_bufname("vscode-userdata:/c%3A/Users/zaube/AppData/Roaming/Code/User/settings.json")
assert uri.scheme == "vscode-userdata", (uri.scheme, uri.path)
assert uri.path == r"/c:/Users/zaube/AppData/Roaming/Code/User/settings.json", ("path", path)

print("Complete Test")
