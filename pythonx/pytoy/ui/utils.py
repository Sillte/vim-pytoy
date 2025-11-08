"""Utils regarding  
"""
import re
from pathlib import Path
from pytoy.ui.ui_enum import UIEnum, get_ui_enum


_pattern = re.compile(r"^vscode\-remote://[^/]+")

def to_filename(path: str | Path) -> Path:
    """Normalize vscode-remote URI into an in-container absolute path.
    Example:
      vscode-remote://wsl%2BUbuntu/home/user/foo.py -> /home/user/foo.py
      vscode-remote://dev-container+abc123/home/app/foo.py -> /home/app/foo.py
      
    NOTE: 
    `to_filename` comes from the domain of VSCode, 
    and it is understandable in the domain of vim/nvim.
    * https://code.visualstudio.com/api/references/vscode-api#TextDocument
    """
    path_str = str(path)
    if get_ui_enum() == UIEnum.VSCODE:
        path_str = _pattern.sub("", path_str)
    return Path(path_str)

def is_remote() -> bool:
    """Return whther the environment is remote or not.
    """
    if get_ui_enum() == UIEnum.VSCODE:
        pass
    from pytoy.ui.vscode.api import Api
    val = Api().eval_with_return("vscode.env.remoteName")
    return bool(val)





if __name__ == "__main__":
    pass

