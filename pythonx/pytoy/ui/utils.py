"""Utils regarding  
"""
import re
from pathlib import Path
from pytoy.ui.ui_enum import UIEnum, get_ui_enum #  NOQA


_pattern = re.compile(r"^vscode\-remote://wsl%2B[^/]+")
def normalize_path(path: str | Path)  -> Path:
    """Returns the normalized path,
    where this library is used in `vscode-plugin`,  
    """
    if get_ui_enum() == UIEnum.VSCODE:
        path = _pattern.sub("", str(path))
        return Path(path)
    return Path(path)

if __name__ == "__main__":
    pass

