from pathlib import Path
from typing import Literal, Any, Mapping, assert_never
import json


class FileReader:
    def __init__(self, local_config_folder: Path, global_config_folder: Path):
        self._local_config_folder = local_config_folder
        self._global_config_folder = global_config_folder

    def read_text(self, path: str | Path, encoding=None) -> str:
        return self._solve_path(path).read_text(encoding=encoding)

    def read_bytes(self, path: str | Path) -> bytes:
        return self._solve_path(path).read_bytes()

    @property
    def local_folder(self) -> Path:
        return self._local_config_folder

    @property
    def global_folder(self) -> Path:
        return self._global_config_folder

    def _solve_path(self, path: str | Path) -> Path:
        path = Path(path)
        _validate_safe_relative_path(path)
        for cand in [self._local_config_folder, self._global_config_folder]:
            if (goal:=(cand / path)).exists():
                return goal
        msg = f"In `{path=}` file does not exist."
        raise OSError(msg)


class ConfigReader:
    def __init__(self, local_config_folder: Path, global_config_folder: Path):
        self._local_config_folder = local_config_folder
        self._global_config_folder = global_config_folder

    def read_json_dict(self, path: str | Path, *, encoding=None) -> dict[str, Any]:
        path = Path(path)

        _validate_safe_relative_path(path)

        def _try_read_dict(parent: Path) -> Mapping | None:
            if ((filepath := parent / path).exists()):
                target = json.loads(filepath.read_text(encoding=encoding))
                if not isinstance(target, Mapping):
                    msg = f"Only mapping is allowed for `{filepath=}`"
                    raise RuntimeError(msg)
            else:
                target = None
            return target
        local_dict = _try_read_dict(self._local_config_folder)
        global_dict = _try_read_dict(self._global_config_folder)

        if local_dict is None and global_dict is None:
            msg = f"`{path=}` does not exist locally nor globally, `{self._local_config_folder=}`, `{self._global_config_folder}`"
            raise ValueError(msg)

        local_dict = local_dict or {}
        global_dict = global_dict or {}
        # The content of `local_dict` has the higher priority. 
        return dict(**global_dict, **local_dict)


class PytoyConfiguration:
    """This class solves the specification of configuration.
    Global / Local configuration is solved. 
    
    """
    NAME = "vim_pytoy" 

    def __init__(self, local_folder: str | Path | None = None):
        self._local_folder = self._solve_local_folder(local_folder)
        self._global_folder = Path.home() / ".config" / self.NAME
    
    def _solve_local_folder(self, local_folder: str | Path | None = None) -> Path:
        if local_folder is None:
            local_folder = Path.cwd()
        local_folder = Path(local_folder)
        required_name = f".{self.NAME}"
        if local_folder.name == required_name:
            return local_folder.absolute()
        else:
            return (local_folder / required_name).absolute()
 
    @property
    def global_folder(self) -> Path:
        self._global_folder.mkdir(exist_ok=True, parents=True)
        return self._global_folder

    @property
    def local_folder(self) -> Path:
        return self._local_folder

    @property
    def file_reader(self) -> FileReader:
        return FileReader(self.local_folder, self.global_folder)

    @property
    def config_reader(self) -> ConfigReader:
        return ConfigReader(self.local_folder, self.global_folder)

    def get_folder(self, relative_path: Path | str, location: Literal["global", "local"] ="local"):
        """Returns the folder, under the config folder.
        This is expected to be used to prepare the sub-configuration folder 
        for each application. 

        This method ensures the folder exists.
        """
        path = Path(relative_path)

        _validate_safe_relative_path(path)

        match location:
            case "global":
                folder = self._global_folder / relative_path
            case "local":
                folder = self._local_folder / relative_path
            case _: 
                assert_never(location)
        folder.mkdir(exist_ok=True, parents=True)
        return folder


def _validate_safe_relative_path(path: Path):
    if path.is_absolute():
        raise ValueError(f"Only relative paths are allowed: {path}")
    if ".." in path.parts:
        raise ValueError(f"Directory traversal ('..') is not allowed: {path}")

