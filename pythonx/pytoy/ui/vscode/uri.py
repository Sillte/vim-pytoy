from pydantic import BaseModel, ConfigDict, model_validator


import re
from pathlib import Path
from typing import Self


class Uri(BaseModel):
    path: str = ""  # Some `scheme` does not have the path.
    scheme: str
    fsPath: str | None = None

    model_config = ConfigDict(extra="allow", frozen=True)

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
                # Remove `Authority`.
                if path.startswith("//"):
                    if (start := path[2:].find("/")) != -1:
                        path = path[2 + start :]
                return cls(path=unquote(path), scheme=scheme)
        # without scheme.
        return cls(path=unquote(bufname), scheme="file")

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
        return Path(filepath.strip("/")).resolve().as_posix()