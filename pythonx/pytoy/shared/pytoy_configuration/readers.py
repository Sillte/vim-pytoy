import json
from pathlib import Path
from typing import Any, Literal, Mapping, assert_never


def validate_safe_relative_path(path: Path | str, base_folder: Path) -> Path:
    """Return a resolved path that stays inside ``base_folder``."""
    path = Path(path)
    abs_path = (base_folder / path).resolve()
    base_resolved = base_folder.resolve()
    try:
        abs_path.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError(f"Path must stay inside {base_resolved}: {path}") from exc
    return abs_path


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
        for candidate_folder in [self._local_config_folder, self._global_config_folder]:
            candidate_path = validate_safe_relative_path(path, candidate_folder)
            if candidate_path.exists():
                return candidate_path
        raise OSError(f"In `{path=}` file does not exist.")


class ConfigReader:
    def __init__(self, local_config_folder: Path, global_config_folder: Path):
        self._local_config_folder = local_config_folder
        self._global_config_folder = global_config_folder

    def read_json_dict(self, path: str | Path, *, encoding=None) -> dict[str, Any]:
        path = Path(path)

        def try_read_dict(parent: Path) -> Mapping | None:
            filepath = validate_safe_relative_path(path, parent)
            if not filepath.exists():
                return None
            text = filepath.read_text(encoding=encoding)
            if not text.strip():
                return None
            target = json.loads(text)
            if not isinstance(target, Mapping):
                raise RuntimeError(f"Only mapping is allowed for `{filepath=}`")
            return target

        local_dict = try_read_dict(self._local_config_folder)
        global_dict = try_read_dict(self._global_config_folder)

        if local_dict is None and global_dict is None:
            raise ValueError(
                f"`{path=}` does not exist locally nor globally, "
                f"`{self._local_config_folder=}`, `{self._global_config_folder}`"
            )

        return dict(**(global_dict or {}), **(local_dict or {}))


class ConfigWriter:
    """Safely write JSON-based configuration files."""

    def __init__(self, local_config_folder: Path, global_config_folder: Path):
        self._local_config_folder = local_config_folder
        self._global_config_folder = global_config_folder

    def assure_json_dict(
        self,
        path: str | Path,
        data: Mapping[str, Any] | None = None,
        location: Literal["local", "global"] = "local",
    ) -> Path:
        if data is None:
            data = {}
        if not isinstance(data, Mapping):
            raise TypeError(f"Only mapping is allowed for writing: got {type(data)}")
        file_path = self.get_path(path, location)
        if not file_path.exists():
            with open(file_path, "w", encoding="utf8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
        return file_path

    def get_path(self, path: str | Path, location: Literal["local", "global"] = "local") -> Path:
        match location:
            case "local":
                base_folder = self._local_config_folder
            case "global":
                base_folder = self._global_config_folder
            case _:
                assert_never(location)
        file_path = validate_safe_relative_path(path, base_folder)
        file_path.parent.mkdir(exist_ok=True, parents=True)
        return file_path
