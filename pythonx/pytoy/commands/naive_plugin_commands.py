from functools import lru_cache
from typing import Annotated, Sequence

from pytoy.shared.command import App, Argument

app = App()


@lru_cache
def _plugin_handler():
    from pytoy.tools.naive_plugin import NaivePluginHandler

    return NaivePluginHandler.from_folders()


def _complete_plugin_names() -> Sequence[str]:
    return _plugin_handler().names


@app.command("NaivePluginRun")
def run_naive_plugin(name: Annotated[str, Argument(completer=_complete_plugin_names)]) -> None:
    _plugin_handler().run(name)


@app.command("NaivePluginExample")
def make_example() -> None:
    from pytoy.tools.naive_plugin import NaivePluginHandler

    NaivePluginHandler.dump_default_examples()
