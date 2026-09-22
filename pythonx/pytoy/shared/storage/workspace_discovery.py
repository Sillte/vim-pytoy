import json
from pathlib import Path
from typing import Any


def find_workspace(start_path: str | Path) -> Path:
    """Find the workspace containing ``start_path``.

    Git repositories take precedence over language-specific workspace markers.
    If neither marker is found, the existing directory or the parent of an
    existing file is used.
    """
    start_folder = _to_start_folder(start_path)
    parents = [start_folder, *start_folder.parents]

    for parent in parents:
        if (parent / ".git").exists():
            return parent

    for parent in parents:
        if _has_uv_workspace(parent):
            return parent

    for parent in parents:
        if (parent / "uv.lock").is_file():
            return parent

    for parent in parents:
        if _has_uv_configuration(parent):
            return parent

    for parent in parents:
        if _has_rust_workspace(parent) or _has_typescript_workspace(parent):
            return parent

    return start_folder


def _to_start_folder(start_path: str | Path) -> Path:
    path = Path(start_path).expanduser().resolve()
    if path.exists() and path.is_file():
        return path.parent
    return path


def _load_pyproject(folder: Path) -> dict[str, Any] | None:
    pyproject_path = folder / "pyproject.toml"
    if not pyproject_path.is_file():
        return None
    try:
        import tomllib

        with pyproject_path.open("rb") as file:
            return tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _has_uv_workspace(folder: Path) -> bool:
    document = _load_pyproject(folder)
    if document is None:
        return False

    tool = document.get("tool", {})
    uv = tool.get("uv") if isinstance(tool, dict) else None
    return isinstance(uv, dict) and isinstance(uv.get("workspace"), dict)


def _has_uv_configuration(folder: Path) -> bool:
    """Return whether ``folder`` has uv configuration without a package."""
    document = _load_pyproject(folder)
    if document is None or isinstance(document.get("project"), dict):
        return False

    tool = document.get("tool", {})
    uv = tool.get("uv") if isinstance(tool, dict) else None
    return isinstance(uv, dict)


def _has_rust_workspace(folder: Path) -> bool:
    document = _load_toml(folder / "Cargo.toml")
    return isinstance(document, dict) and isinstance(document.get("workspace"), dict)


def _has_typescript_workspace(folder: Path) -> bool:
    if (folder / "pnpm-workspace.yaml").is_file():
        return True

    package_json = _load_json(folder / "package.json")
    if isinstance(package_json, dict) and "workspaces" in package_json:
        return isinstance(package_json["workspaces"], (list, dict))

    tsconfig = _load_json(folder / "tsconfig.json")
    if isinstance(tsconfig, dict):
        return isinstance(tsconfig.get("references"), list)
    return False


def _load_toml(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        import tomllib

        with path.open("rb") as file:
            return tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf8") as file:
            document = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    return document if isinstance(document, dict) else None
