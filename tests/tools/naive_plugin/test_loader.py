from pathlib import Path
from types import FunctionType, SimpleNamespace
from typing import cast

import pytest

from pytoy.tools.naive_plugin import (
    InvalidNaivePluginError,
    NaivePluginContext,
    NaivePluginHandler,
    NaivePluginLoader,
    NaivePluginNotFoundError,
    register_naive_plugin,
)


def _write_plugin(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")


def test_loads_multiple_named_plugins_from_one_file(tmp_path: Path) -> None:
    _write_plugin(
        tmp_path / "plugins.py",
        """
from pytoy.tools.naive_plugin import register_naive_plugin

@register_naive_plugin(name="first")
def first(context):
    context.called = "first"

@register_naive_plugin(name="second")
def second(context):
    context.called = "second"
""",
    )

    plugins = NaivePluginLoader().load_plugins(tmp_path)
    assert sorted(plugins) == ["first", "second"]
    context = SimpleNamespace()
    plugins["second"](cast(NaivePluginContext, context))
    assert context.called == "second"


@pytest.mark.parametrize(
    "sources",
    [
        {
            "plugins.py": """
from pytoy.tools.naive_plugin import register_naive_plugin

@register_naive_plugin(name="duplicate")
def first(context): pass

@register_naive_plugin(name="duplicate")
def second(context): pass
"""
        },
        {
            "first.py": """
from pytoy.tools.naive_plugin import register_naive_plugin

@register_naive_plugin(name="duplicate")
def first(context): pass
""",
            "second.py": """
from pytoy.tools.naive_plugin import register_naive_plugin

@register_naive_plugin(name="duplicate")
def second(context): pass
""",
        },
    ],
)
def test_duplicate_names_in_one_folder_are_rejected(
    tmp_path: Path,
    sources: dict[str, str],
) -> None:
    for filename, source in sources.items():
        _write_plugin(tmp_path / filename, source)

    with pytest.raises(InvalidNaivePluginError, match="Duplicate naive plugin name"):
        NaivePluginLoader().load_plugins(tmp_path)


def test_handler_uses_later_folder_for_duplicate_plugin_names(tmp_path: Path) -> None:
    global_folder = tmp_path / "global"
    local_folder = tmp_path / "local"
    global_folder.mkdir()
    local_folder.mkdir()
    _write_plugin(
        global_folder / "plugins.py",
        """
from pytoy.tools.naive_plugin import register_naive_plugin

@register_naive_plugin(name="shared")
def global_plugin(context):
    context.called = "global"

@register_naive_plugin(name="global_only")
def global_only(context): pass
""",
    )
    _write_plugin(
        local_folder / "plugins.py",
        """
from pytoy.tools.naive_plugin import register_naive_plugin

@register_naive_plugin(name="shared")
def local_plugin(context):
    context.called = "local"

@register_naive_plugin(name="local_only")
def local_only(context): pass
""",
    )

    handler = NaivePluginHandler.from_folders(plugin_folders=(global_folder, local_folder))

    assert handler._list_plugins() == ("global_only", "local_only", "shared")
    context = SimpleNamespace()
    handler._get("shared")(cast(NaivePluginContext, context))
    assert context.called == "local"


def test_handler_copies_plugin_mapping() -> None:
    def plugin(context: NaivePluginContext) -> None:
        pass

    plugins = {"example": plugin}
    handler = NaivePluginHandler(plugins)
    plugins.clear()

    assert handler._get("example") is plugin


def test_handler_raises_for_unknown_plugin() -> None:
    handler = NaivePluginHandler({})

    with pytest.raises(NaivePluginNotFoundError, match="not found"):
        handler._get("missing")


def test_decorator_rejects_invalid_name_at_definition_time() -> None:
    with pytest.raises(ValueError, match="Invalid naive plugin name"):
        register_naive_plugin(name="../escape")


def test_dump_default_examples_writes_loadable_examples(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pytoy.tools.naive_plugin.handler as handler_module

    plugin_folder = tmp_path / "naive_plugins"
    plugin_folder.mkdir()
    monkeypatch.setattr(
        handler_module,
        "PytoyConfiguration",
        lambda: SimpleNamespace(
            get_folder=lambda relative_path, location: plugin_folder,
        ),
    )

    NaivePluginHandler.dump_default_examples()

    example_path = plugin_folder / "example.py"
    example2_path = plugin_folder / "example2.py"
    assert example_path.is_file()
    assert example2_path.is_file()
    assert 'register_naive_plugin(name="example")' in example_path.read_text(encoding="utf-8")
    example2_source = example2_path.read_text(encoding="utf-8")
    assert 'get_folder("naive_plugins", location="global")' in example2_source
    assert "PytoyWindow.open(example_path)" in example2_source
    plugins = NaivePluginLoader().load_plugins(plugin_folder)
    assert plugins.keys() == {"example", "example2"}

    opened_paths: list[Path] = []
    example2_plugin = plugins["example2"]
    assert isinstance(example2_plugin, FunctionType)
    example2_plugin.__globals__["PytoyConfiguration"] = lambda: SimpleNamespace(
        get_folder=lambda relative_path, location: plugin_folder
    )
    example2_plugin.__globals__["PytoyWindow"] = SimpleNamespace(open=opened_paths.append)
    example2_plugin(cast(NaivePluginContext, SimpleNamespace()))

    output_path = plugin_folder / "example2.txt"
    assert output_path.read_text(encoding="utf-8") == "This file was created by naive plugin example2.\n"
    assert opened_paths == [output_path]


def test_dump_default_examples_does_not_overwrite_existing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pytoy.tools.naive_plugin.handler as handler_module

    plugin_folder = tmp_path / "naive_plugins"
    plugin_folder.mkdir()
    example_path = plugin_folder / "example.py"
    example_path.write_text("# user plugin\n", encoding="utf-8")
    monkeypatch.setattr(
        handler_module,
        "PytoyConfiguration",
        lambda: SimpleNamespace(
            get_folder=lambda relative_path, location: plugin_folder,
        ),
    )

    NaivePluginHandler.dump_default_examples()

    assert example_path.read_text(encoding="utf-8") == "# user plugin\n"
    assert (plugin_folder / "example2.py").is_file()
