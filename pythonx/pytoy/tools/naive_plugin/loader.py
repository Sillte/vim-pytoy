from __future__ import annotations

import hashlib
import importlib.util
import inspect
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

from .exceptions import (
    InvalidNaivePluginError,
    NaivePluginLoadError,
)
from .models import _NAIVE_PLUGIN_NAME, NaivePluginContext, _is_valid_plugin_name

PluginFunction = Callable[[NaivePluginContext], None]


class NaivePluginLoader:
    """Discover and load function-based naive plugins from a directory."""

    @staticmethod
    def is_valid_name(name: str) -> bool:
        return _is_valid_plugin_name(name)

    def load_plugins(self, plugin_directory: Path) -> dict[str, PluginFunction]:
        """Load all plugin functions from one directory."""
        return self._load_directory(plugin_directory)

    def _load_directory(self, plugin_directory: Path) -> dict[str, PluginFunction]:
        plugins: dict[str, PluginFunction] = {}
        for plugin_path in sorted(plugin_directory.glob("*.py")):
            if plugin_path.stem.startswith("_") or not plugin_path.is_file():
                continue
            module = self._load_module(plugin_path)
            for name, function in self._find_plugins(module, plugin_path):
                if name in plugins:
                    raise InvalidNaivePluginError(f"Duplicate naive plugin name {name!r} in {plugin_directory}")
                plugins[name] = function
        return plugins

    @staticmethod
    def _find_plugins(module: ModuleType, plugin_path: Path) -> tuple[tuple[str, PluginFunction], ...]:
        plugins: list[tuple[str, PluginFunction]] = []
        seen: set[int] = set()
        for candidate in vars(module).values():
            name = getattr(candidate, _NAIVE_PLUGIN_NAME, None)
            if name is None or getattr(candidate, "__module__", None) != module.__name__:
                continue
            if id(candidate) in seen:
                continue
            seen.add(id(candidate))
            if not inspect.isfunction(candidate) or not NaivePluginLoader.is_valid_name(name):
                raise InvalidNaivePluginError(f"Invalid naive plugin definition in {plugin_path}: {name!r}")
            plugins.append((name, cast(PluginFunction, candidate)))
        return tuple(plugins)

    def _load_module(self, plugin_path: Path) -> ModuleType:
        resolved_path = plugin_path.resolve()
        path_hash = hashlib.sha256(str(resolved_path).encode("utf-8")).hexdigest()
        try:
            source = plugin_path.read_bytes()
        except OSError as error:
            raise NaivePluginLoadError(f"Failed to read naive plugin from {plugin_path}") from error
        content_hash = hashlib.sha256(source).hexdigest()
        cache_prefix = f"_pytoy_naive_plugin_{path_hash}_"
        module_name = f"{cache_prefix}{content_hash}"
        cached_module = sys.modules.get(module_name)
        if isinstance(cached_module, ModuleType):
            return cached_module

        for cached_name in tuple(sys.modules):
            if cached_name.startswith(cache_prefix):
                sys.modules.pop(cached_name, None)

        spec = importlib.util.spec_from_file_location(module_name, plugin_path)
        if spec is None or spec.loader is None:
            raise NaivePluginLoadError(f"Cannot load naive plugin from {plugin_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            exec(compile(source, str(plugin_path), "exec"), module.__dict__)
        except Exception as error:
            sys.modules.pop(module_name, None)
            raise NaivePluginLoadError(f"Failed to import naive plugin from {plugin_path}") from error
        return module
