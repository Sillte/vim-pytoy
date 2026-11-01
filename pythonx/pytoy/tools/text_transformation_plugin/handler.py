from __future__ import annotations

from pathlib import Path
from typing import Self

from pytoy.shared.pytoy_configuration import PytoyConfiguration

from .exceptions import InvalidTextTransformationResultError, TextTransformationNotFoundError
from .loader import TextTransformationLoader


class TextTransformationHandler:
    """Discover and run named text transformations."""

    def __init__(self, plugin_directory: Path, *, loader: TextTransformationLoader | None = None) -> None:
        self._plugin_directory = plugin_directory
        self._loader = loader or TextTransformationLoader()

    @classmethod
    def from_global_folder(cls) -> Self:
        configuration = PytoyConfiguration()
        plugin_directory = configuration.get_folder("text_transformation_plugins", location="global")
        return cls(plugin_directory)

    @property
    def names(self) -> tuple[str, ...]:
        return self._loader.discover_names(self._plugin_directory)

    @property
    def plugin_directory(self) -> Path:
        return self._plugin_directory

    def dump_default_examples(self) -> bool:
        example_path = self._plugin_directory / "example.py"
        example_source = r"""from pytoy.tools.text_transformation_plugin import register_text_transformation


@register_text_transformation(name="uppercase")
def uppercase(content: str) -> str:
    return content.upper()


@register_text_transformation(name="replace_foo")
def replace_foo(content: str) -> str:
    return content.replace("foo", "bar")
"""
        try:
            with example_path.open("x", encoding="utf-8") as example_file:
                example_file.write(example_source)
        except FileExistsError:
            return False
        return True

    def transform(self, name: str, content: str) -> str:
        plugins = self._loader.load_plugins(self._plugin_directory)
        try:
            transformation = plugins[name]
        except KeyError:
            raise TextTransformationNotFoundError(f"Text transformation not found: {name}") from None

        result = transformation(content)
        if not isinstance(result, str):
            raise InvalidTextTransformationResultError(
                f"Text transformation {name!r} returned {type(result).__name__}, expected str"
            )
        return result
