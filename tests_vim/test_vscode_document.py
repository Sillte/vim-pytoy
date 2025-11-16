from pathlib import Path
from pytoy.ui.vscode.uri import Uri

uri = Uri.from_bufname(r"c:\LocalLibrary\PublicLibrary\vim-pytoy\search-editor:#0.8964251299312702")
assert uri.scheme == "search-editor", uri

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
assert uri.path == r"/c:/Users/zaube/AppData/Roaming/Code/User/settings.json", ("path", uri.path)


uri = Uri.from_bufname("/mnt/c/Users/zaube/AppData/Local/Programs/Microsoft VS Code/untitled:__pystderr__")
assert uri.scheme == "untitled", (uri.scheme, uri.path)
assert uri.path == "__pystderr__", uri


uri = Uri.from_bufname("vscode-remote://wsl%2Bubuntu/home/zaube/vim-pytoy/pythonx/pytoy/ui/vscode/document.py")
assert uri.scheme == "vscode-remote", (uri.scheme, uri.path)
assert uri.path == "/home/zaube/vim-pytoy/pythonx/pytoy/ui/vscode/document.py", uri


print("Complete Test")
