from typing import Annotated

from pytoy.shared.command.app.impls.vim import VimCommandAdapter
from pytoy.shared.command.core.models import Argument, CommandModel


def _command(plugin_name: Annotated[str, Argument(completer=lambda: ["example"])]) -> None: ...


def test_command_completion_strips_visual_range_prefix(monkeypatch) -> None:
    name = "BrowserInvoke"
    monkeypatch.setitem(VimCommandAdapter.COMMAND_MAPS, name, CommandModel.from_callable(_command))
    cmd_line = "'<,'>BrowserInvoke ex"

    candidates = VimCommandAdapter.complete_command(name, "example", cmd_line, len(cmd_line))

    assert candidates == ["example"]
