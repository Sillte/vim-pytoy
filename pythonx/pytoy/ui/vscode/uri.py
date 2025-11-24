from pydantic import BaseModel, ConfigDict, model_validator


import re
from pathlib import Path
from typing import Self, Sequence

from pytoy.ui.vscode.api import Api


class Uri(BaseModel):
    scheme: str
    path: str = ""  # Some `scheme` may not have the path.
    authority: str = "" # Some `scheme` does not have the path.
    fsPath: str | None = None

    model_config = ConfigDict(extra="allow", frozen=True)
    
    def to_key_str(self, ) -> str:
        """Return the argement of `vscode.Uri.parse`. 
        """
        authority = self.authority or ""  # To be safe.  
        separator =  "://" if authority else ":"
        return f"{self.scheme}{separator}{authority}{self.path}"


    @classmethod
    def from_bufname(cls, bufname: str) -> Self:
        """Convert the name of buffer to `Uri`.
        This strongly depends specifications of `vscode-neovim extension`.
        """
        from urllib.parse import unquote

        # See the test.
        # For windows path case, the first is not regarded as the scheme.
        pattern1 = r"^[a-zA-Z]:[\\\/](.*?)[\\\/](?P<scheme>[a-zA-Z-_]+):(?P<path>.*)#?(?P<fragment>.*)"
        # Non-windows path with scheme
        pattern2 = r"(?![a-zA-Z]:[\\\/])(?:(.*?)[\\\/])?(?P<scheme>[a-zA-Z-_]+):(?P<path>.*)#?(?P<fragment>.*)"
        for pattern in [pattern1, pattern2]:
            if m := re.match(pattern, bufname):
                path = m.group("path")
                scheme = m.group("scheme")
                # Separate `Authority`.
                if path.startswith("//"):
                    if (start := path[2:].find("/")) != -1:
                        path, authority = path[2 + start :], path[2: 2 + start]
                    else:
                        authority = ""
                else:
                    authority = ""
                return cls(path=unquote(path), scheme=scheme, authority=unquote(authority))
        # without scheme.
        return cls(path=unquote(bufname), scheme="file", authority="")
    
    @classmethod
    def from_filepath(cls, path: str | Path) -> Self: 
        if not is_remote_vscode():
            return cls(scheme="file", path=Path(path).as_posix(), authority="")
        authority = get_remote_authority()
        return cls(scheme="vscode-remote", path=Path(path).as_posix(), authority=authority)

    @classmethod
    def from_untitled_name(cls, name: str) -> Self: 
        return cls(scheme="untitled", path=name, authority="")


    @model_validator(mode="after")
    def set_fs_path_if_file(self) -> Self:
        if self.scheme == "file":
            if self.fsPath is None:
                object.__setattr__(self, "fsPath", self.path)
        return self

    def __eq__(self, other) -> bool:
        if isinstance(other, Uri):
            if self.scheme == "file":
                return (self._norm_filepath(self.path), self.scheme) == (
                    self._norm_filepath(other.path),
                    other.scheme,
                )
            else:
                return (self.path, self.scheme) == (other.path, other.scheme)
        return False

    def __hash__(self) -> int:
        if self.scheme == "file":
            return hash((self._norm_filepath(self.path), self.scheme))
        else:
            return hash((self.path, self.scheme))

    def _norm_filepath(self, filepath: str) -> str:
        # There is a discrepancy for `case-sensitivy` and strip of `/`.
        return str(Path(filepath.strip("/")).resolve()).lower()
    
    @classmethod
    def get_uris(cls) -> Sequence[Self]:
        api = Api()
        jscode = "vscode.workspace.textDocuments.map(doc => {return doc.uri;});"
        return [cls.model_validate(elem) for elem in api.eval_with_return(jscode, with_await=False)]

def is_remote_vscode() -> bool:
    return bool(Api().eval_with_return("vscode.env.remoteName"))

def get_remote_authority() -> str:
    if not is_remote_vscode():
        return ""
    
    uris = Uri.get_uris()
    uris = [uri for uri in uris if uri.scheme == "vscode-remote"]
    authorities = set(uri.authority for uri in uris)
    if 2 <= len(authorities):
        msg = f"`{authorities}` are found, it is impossible to determine autority."
        raise ValueError(msg)
    elif 1 == len(authorities): 
        return list(authorities)[0]

    # Inference based on working folder.
    api = Api()
    jscode = "vscode.workspace.workspaceFolders.map(folder => {folder.uri});"
    uris = [Uri.model_validate(elem) for elem in api.eval_with_return(jscode, with_await=False)]
    uris = [uri for uri in uris if uri.scheme == "vscode-remote"]
    authorities = set(uri.authority for uri in uris)
    if 2 <= len(authorities):
        msg = f"`{authorities}` are found, it is impossible to determine autority."
        raise ValueError(msg)
    elif 1 == len(authorities): 
        return list(authorities)[0]
    return ""

