import re
from collections.abc import Callable
from dataclasses import dataclass

from pytoy.shared.lib.text import CharacterRange
from pytoy.shared.ui import PytoyBuffer, PytoyWindow

_NAIVE_PLUGIN_NAME = "__pytoy_naive_plugin_name__"
_PLUGIN_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


@dataclass(frozen=True)
class NaivePluginContext:
    current_buffer: PytoyBuffer
    current_window: PytoyWindow

    @property
    def selection(self) -> CharacterRange:
        return self.current_window.selection


def _is_valid_plugin_name(name: object) -> bool:
    return isinstance(name, str) and _PLUGIN_NAME_PATTERN.fullmatch(name) is not None


def register_naive_plugin(
    name: str,
) -> Callable[[Callable[[NaivePluginContext], None]], Callable[[NaivePluginContext], None]]:
    """Mark a function for discovery as a named naive plugin."""
    if not _is_valid_plugin_name(name):
        raise ValueError(f"Invalid naive plugin name: {name!r}")

    def decorator(
        function: Callable[[NaivePluginContext], None],
    ) -> Callable[[NaivePluginContext], None]:
        setattr(function, _NAIVE_PLUGIN_NAME, name)
        return function

    return decorator
