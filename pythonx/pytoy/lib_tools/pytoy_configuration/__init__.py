from pathlib import Path
from typing import Literal, Any, Mapping, assert_never, Sequence
import json
import time
import shutil 
import hashlib

type LocalConfigType = Literal["project", "centralized"]


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
        for cand in [self._local_config_folder, self._global_config_folder]:
            goal = _validate_safe_relative_path(path, cand)
            if goal.exists():
                return goal
        msg = f"In `{path=}` file does not exist."
        raise OSError(msg)


class ConfigReader:
    def __init__(self, local_config_folder: Path, global_config_folder: Path):
        self._local_config_folder = local_config_folder
        self._global_config_folder = global_config_folder

    def read_json_dict(self, path: str | Path, *, encoding=None) -> dict[str, Any]:
        path = Path(path)

        def _try_read_dict(parent: Path) -> Mapping | None:
            filepath = _validate_safe_relative_path(path, parent)
            if filepath.exists():
                text = filepath.read_text(encoding=encoding)
                if not text.strip():
                    target = None
                else:
                    target = json.loads(text)
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
    
class ConfigWriter:
    """
    ConfigWriter allows safely writing JSON-based configuration files
    into local or global configuration folders.
    """
    def __init__(self, local_config_folder: Path, global_config_folder: Path):
        self._local_config_folder = local_config_folder
        self._global_config_folder = global_config_folder

    def assure_json_dict(
        self, 
        path: str | Path, 
        data: Mapping[str, Any] | None = None, 
        location: Literal["local", "global"] = "local",
    ) -> Path:
        """
        Write a dictionary as JSON to the specified location.
        Ensures the path is safe and parent directories exist.
        """
        if data is None:
            data = {}
        if not isinstance(data, Mapping):
            raise TypeError(f"Only mapping is allowed for writing: got {type(data)}")
        file_path = self.get_path(path, location)
        if file_path.exists():
            return file_path
        else:
            with open(file_path, "w", encoding="utf8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        return file_path
    
    def get_path(self,
                 path: str | Path,
                 location: Literal["local", "global"] = "local") -> Path:
        match location:
            case "local":
                base_folder = self._local_config_folder
            case "global":
                base_folder = self._global_config_folder
            case _:
                assert_never(location)
        file_path = _validate_safe_relative_path(path, base_folder)
        file_path.parent.mkdir(exist_ok=True, parents=True)
        return file_path


class CentralizedFolderSolver:
    def __init__(self, global_folder: Path) -> None:
        self._global_folder = global_folder

    @property
    def centralized_locals_root(self) -> Path:
        root = self._global_folder / "locals"
        root.mkdir(exist_ok=True, parents=True)
        return root
    
    def get_centralized_folder(self, local_folder: Path) -> Path:
        key = hashlib.sha1(local_folder.absolute().as_posix().encode("utf8")).hexdigest()
        concrete_folder = self.centralized_locals_root / key
        self._touch_for_centralizd_local(concrete_folder, local_folder)
        return concrete_folder

    def _touch_for_centralizd_local(self, centralized_local_folder: Path, local_folder: Path):
        centralized_local_folder.mkdir(exist_ok=True, parents=True)
        folder_path = local_folder.absolute().as_posix()
        timestamp = str(time.time())
        origin_txt = self._to_origin_path(centralized_local_folder)
        origin_txt.write_text("\n".join([folder_path, timestamp]))
        
    def _to_origin_path(self, folder: Path) -> Path:
        return folder / "origin.txt"
    
    def clean_locals(self, expire_days: float = 1) -> None:
        """
        Remove centralized local config folders whose origin.txt
        has not been updated within `expire_days`.
        """
        now = time.time()
        expire_seconds = expire_days * 24 * 60 * 60
        
        def _is_remain(origin_path: Path) -> bool:
            if origin_path.exists():
                try:
                    last_used = origin_path.stat().st_mtime
                except OSError:
                    return False
                else:
                    if now - last_used < expire_seconds:
                        return True
            return False

        root = self.centralized_locals_root
        for folder in root.iterdir():
            if not folder.is_dir():
                continue
            origin_txt = self._to_origin_path(folder)
            if not _is_remain(origin_txt):
                shutil.rmtree(folder, ignore_errors=True)


class PytoyConfiguration:
    """This class solves the specification of configuration.
    Global / Local configuration is solved. 
    
    """
    NAME = "vim_pytoy" 

    def __init__(self,
                local_folder: str | Path | None = None,
                local_config_type: LocalConfigType | None = None):
        self.local_config_type = self._solve_local_config_mode(local_config_type, local_folder)
        self._local_folder = self._solve_local_folder(local_folder, self.local_config_type)
        self._global_folder = Path.home() / ".config" / self.NAME
        
    def _solve_local_config_mode(self, config_type: LocalConfigType | None, local_folder: str | Path | None = None) -> LocalConfigType:
        if config_type is not None:
            return config_type
        # In case where there is no specification, it is checked whether
        # If `local_folder` already exists in the project folder or not.
        cand_folder = self._solve_local_folder(local_folder, local_config_type="project")
        if cand_folder.exists():
            return "project"
        return "centralized"
    
    def _solve_local_folder(self, local_folder: str | Path | None = None, local_config_type: LocalConfigType= "project") -> Path:
        if local_folder is None:
            local_folder = Path.cwd()
        local_folder = Path(local_folder)
        required_name = f".{self.NAME}"
        match local_config_type:
            case "project":
                if local_folder.name == required_name:
                    return local_folder.absolute()
                else:
                    return (local_folder / required_name).absolute()
            case "centralized":
                solver = CentralizedFolderSolver(self.global_folder)
                return solver.get_centralized_folder(local_folder)
            case _:
                assert_never(local_config_type)

    def clean_centralized_locals(self, expire_days: float = 1) -> None:
        CentralizedFolderSolver(self.global_folder).clean_locals(expire_days)
        
    def fetch_local_to_project(self, remove_source: bool = True) -> None:
        solver = CentralizedFolderSolver(self.global_folder)
        src_folder = solver.get_centralized_folder(self.local_folder)
        if not src_folder.exists():
            raise ValueError(f"`{self.local_folder}` does not have the config in the centralized repository.")
        dst_folder = self._solve_local_folder(self.local_folder, local_config_type="project")
        _merge_copy(src_folder, dst_folder, remove_source=remove_source)

    def move_local_to_centralized(self, remove_source: bool = False) -> None:
        solver = CentralizedFolderSolver(self.global_folder)
        src_folder = self._solve_local_folder(self.local_folder, local_config_type="project")
        if not src_folder.exists():
            raise ValueError(f"`{self.local_folder}` does not have the config in the project")
        dst_folder = solver.get_centralized_folder(self.local_folder)
        _merge_copy(src_folder, dst_folder, remove_source=remove_source)
 
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

    @property
    def config_reader(self) -> ConfigWriter:
        return ConfigWriter(self.local_folder, self.global_folder)

    def get_folder(self, relative_path: Path | str, location: Literal["global", "local"] ="local"):
        """Returns the folder, under the config folder.
        This is expected to be used to prepare the sub-configuration folder 
        for each application. 

        This method ensures the folder exists.
        """
        match location:
            case "global":
                base_folder = self._global_folder
            case "local":
                base_folder = self._local_folder
            case _: 
                assert_never(location)
        folder = _validate_safe_relative_path(relative_path, base_folder)
        folder.mkdir(exist_ok=True, parents=True)
        return folder


def _validate_safe_relative_path(path: Path | str, base_folder: Path) -> Path:
    """
    Ensure that 'path' is a relative path that stays inside 'base_folder' after resolving.
    """
    path = Path(path)
    abs_path = (base_folder / path).resolve()
    base_resolved = base_folder.resolve()
    try:
        abs_path.relative_to(base_resolved)
    except ValueError:
        raise ValueError(...)
    return abs_path


def _merge_copy(src_folder: Path, dst_folder: Path, remove_source: bool = False) -> None: 
    if src_folder.resolve().is_relative_to(dst_folder.resolve()):
        raise ValueError(f"Destination folder {src_folder} is inside source {dst_folder}. Aborting for inappropriate usage.")

    dst_folder.mkdir(exist_ok=True, parents=True)

    for item in src_folder.iterdir():
        dst_item = dst_folder / item.name
        if item.is_file():
            shutil.copy2(item, dst_item)
        elif item.is_dir():
            shutil.copytree(item, dst_item, dirs_exist_ok=True)
    if remove_source:
        shutil.rmtree(src_folder, ignore_errors=True)
