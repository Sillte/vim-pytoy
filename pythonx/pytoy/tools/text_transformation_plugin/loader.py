from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import sys
from pathlib import Path
from threading import RLock
from types import ModuleType
from typing import cast

from .exceptions import InvalidTextTransformationPluginError, TextTransformationPluginLoadError
from .registry import _TEXT_TRANSFORMATION_NAME, TextTransformation, _is_valid_name

_module_lock = RLock()


class TextTransformationLoader:
    """Load and statically discover transformations in a plugin directory."""

    def discover_names(self, plugin_directory: Path) -> tuple[str, ...]:
        names: set[str] = set()
        for plugin_path in sorted(plugin_directory.glob("*.py")):
            if plugin_path.stem.startswith("_") or not plugin_path.is_file():
                continue
            try:
                source = plugin_path.read_text(encoding="utf-8")
                module = ast.parse(source, filename=str(plugin_path))
            except (OSError, SyntaxError, UnicodeError):
                continue

            registration_aliases = {
                alias.asname or alias.name
                for node in module.body
                if isinstance(node, ast.ImportFrom) and node.module == "pytoy.tools.text_transformation_plugin"
                for alias in node.names
                if alias.name == "register_text_transformation"
            }
            for node in module.body:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for decorator in node.decorator_list:
                    name = self._registered_name(decorator, registration_aliases)
                    if name is not None:
                        names.add(name)

        return tuple(sorted(names))

    @staticmethod
    def _registered_name(decorator: ast.expr, registration_aliases: set[str]) -> str | None:
        if not isinstance(decorator, ast.Call):
            return None
        if not isinstance(decorator.func, ast.Name) or decorator.func.id not in registration_aliases:
            return None

        name_node = next((keyword.value for keyword in decorator.keywords if keyword.arg == "name"), None)
        if name_node is None and decorator.args:
            name_node = decorator.args[0]
        if not isinstance(name_node, ast.Constant) or not isinstance(name_node.value, str):
            return None
        if not _is_valid_name(name_node.value):
            return None
        return name_node.value

    def load_plugins(self, plugin_directory: Path) -> dict[str, TextTransformation]:
        plugins: dict[str, TextTransformation] = {}
        for plugin_path in sorted(plugin_directory.glob("*.py")):
            if plugin_path.stem.startswith("_") or not plugin_path.is_file():
                continue
            module = self._load_module(plugin_path)
            for name, function in self._find_plugins(module, plugin_path):
                if name in plugins:
                    raise InvalidTextTransformationPluginError(
                        f"Duplicate text transformation name {name!r} in {plugin_directory}"
                    )
                plugins[name] = function
        return plugins

    @staticmethod
    def _find_plugins(module: ModuleType, plugin_path: Path) -> tuple[tuple[str, TextTransformation], ...]:
        plugins: list[tuple[str, TextTransformation]] = []
        seen: set[int] = set()
        for candidate in vars(module).values():
            name = getattr(candidate, _TEXT_TRANSFORMATION_NAME, None)
            if name is None or getattr(candidate, "__module__", None) != module.__name__:
                continue
            if id(candidate) in seen:
                continue
            seen.add(id(candidate))
            if not inspect.isfunction(candidate) or not _is_valid_name(name):
                raise InvalidTextTransformationPluginError(
                    f"Invalid text transformation definition in {plugin_path}: {name!r}"
                )
            plugins.append((name, cast(TextTransformation, candidate)))
        return tuple(plugins)

    @staticmethod
    def _load_module(plugin_path: Path) -> ModuleType:
        resolved_path = plugin_path.resolve()
        path_hash = hashlib.sha256(str(resolved_path).encode("utf-8")).hexdigest()
        cache_prefix = f"_pytoy_text_transformation_plugin_{path_hash}_"
        try:
            source = resolved_path.read_bytes()
        except OSError as error:
            raise TextTransformationPluginLoadError(
                f"Failed to read text transformation plugin from {resolved_path}"
            ) from error
        content_hash = hashlib.sha256(source).hexdigest()
        module_name = f"{cache_prefix}{content_hash}"

        with _module_lock:
            cached_module = sys.modules.get(module_name)
            if isinstance(cached_module, ModuleType):
                return cached_module

            for cached_name in tuple(sys.modules):
                if cached_name.startswith(cache_prefix):
                    sys.modules.pop(cached_name, None)

            spec = importlib.util.spec_from_file_location(module_name, resolved_path)
            if spec is None or spec.loader is None:
                raise TextTransformationPluginLoadError(f"Cannot load text transformation plugin from {resolved_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                exec(compile(source, str(resolved_path), "exec"), module.__dict__)
            except Exception as error:
                sys.modules.pop(module_name, None)
                raise TextTransformationPluginLoadError(
                    f"Failed to import text transformation plugin from {resolved_path}"
                ) from error
            return module
