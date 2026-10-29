from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Self, Sequence

from pytoy.shared.pytoy_configuration import PytoyConfiguration
from pytoy.shared.ui import PytoyBuffer, PytoyWindow

from .exceptions import NaivePluginNotFoundError
from .loader import NaivePluginLoader
from .models import NaivePluginContext

PluginFunction = Callable[[NaivePluginContext], None]


class NaivePluginHandler:
    """Load, store, and run named naive plugin functions."""

    def __init__(self, plugins: Mapping[str, PluginFunction]) -> None:
        self._plugins = dict(plugins)

    @classmethod
    def from_folders(cls, *, plugin_folders: Sequence[Path] | None = None) -> Self:
        """Load plugins in folder order; later folders override earlier names."""
        if plugin_folders is None:
            configuration = PytoyConfiguration()
            plugin_folders = (configuration.get_folder("naive_plugins", location="global"),)
        loader = NaivePluginLoader()
        plugins: dict[str, PluginFunction] = dict()
        for plugin_folder in plugin_folders:
            plugins.update(loader.load_plugins(plugin_folder))

        return cls(plugins=plugins)

    @classmethod
    def dump_default_examples(cls) -> None:
        configuration = PytoyConfiguration()
        plugin_folder = configuration.get_folder("naive_plugins", location="global")
        examples = {
            "example.py": """from pytoy.tools.naive_plugin import NaivePluginContext, register_naive_plugin


@register_naive_plugin(name="example")
def example(context: NaivePluginContext) -> None:
    context.current_buffer.append("Naive plugin example executed.\\n")
""",
            "example2.py": """from pytoy.shared.pytoy_configuration import PytoyConfiguration
from pytoy.shared.ui import PytoyWindow
from pytoy.tools.naive_plugin import NaivePluginContext, register_naive_plugin


@register_naive_plugin(name="example2")
def example2(context: NaivePluginContext) -> None:
    configuration = PytoyConfiguration()
    example_path = configuration.get_folder("naive_plugins", location="global") / "example2.txt"
    try:
        with example_path.open("x", encoding="utf-8") as example_file:
            example_file.write("This file was created by naive plugin example2.\\n")
    except FileExistsError:
        pass
    PytoyWindow.open(example_path)
""",
        }
        for filename, source in examples.items():
            example_path = plugin_folder / filename
            try:
                with example_path.open("x", encoding="utf-8") as example_file:
                    example_file.write(source)
            except FileExistsError:
                continue

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._plugins.keys()))

    def run(self, name: str) -> None:
        function = self._get(name)
        context = NaivePluginContext(current_buffer=PytoyBuffer.get_current(), current_window=PytoyWindow.get_current())
        return function(context)

    def _get(self, name: str) -> PluginFunction:
        try:
            return self._plugins[name]
        except KeyError:
            raise NaivePluginNotFoundError(f"Naive plugin not found: {name}") from None
