from pathlib import Path
from types import SimpleNamespace

from pytoy import TERM_STDERR, TERM_STDOUT
from pytoy.commands import console_command
from pytoy.shared.command.core.models import CommandModel
from pytoy.shared.command.service.completion import CompletionParam, CompletionService
from pytoy.shared.ui.pytoy_buffer import BufferSource


def test_hide_scope_completes_literal_values():
    model = CommandModel.from_callable(console_command.hide_buffers)

    result = CompletionService().make_completions(model, CompletionParam(cmd_line="t", cursor_pos=1, offset=0))

    assert {candidate.value for candidate in result.candidates} == {"temporary", "terminal"}


class FakeProvider:
    def __init__(self, buffers):
        self.buffers = buffers
        self.closed = None

    def get_buffers(self, *, is_normal_type: bool):
        assert is_normal_type is False
        return self.buffers

    def close_buffers(self, buffer_ids):
        self.closed = buffer_ids


def make_buffer(name: str, *, is_file: bool = False):
    source = BufferSource.from_path(Path(name)) if is_file else BufferSource.from_no_file(name)
    return SimpleNamespace(buffer_id=name, source=source, is_file=is_file)


def test_hide_temporary_closes_every_double_underscore_non_file_buffer(monkeypatch):
    buffers = [
        make_buffer("__TERMINAL__"),
        make_buffer("__idea_chat__"),
        make_buffer("ordinary"),
        make_buffer("__file__.py", is_file=True),
    ]
    provider = FakeProvider(buffers)
    monkeypatch.setattr("pytoy.shared.ui.pytoy_buffer.PytoyBufferProvider", lambda: provider)
    terminated = []
    monkeypatch.setattr(console_command, "_terminate_matching_executions", lambda selected: terminated.extend(selected))

    console_command.hide_buffers("temporary")

    assert provider.closed == ["__TERMINAL__", "__idea_chat__"]
    assert terminated == [buffers[0], buffers[1]]


def test_hide_terminal_closes_known_terminal_and_output_buffers_only(monkeypatch):
    buffers = [
        make_buffer("__TERMINAL__"),
        make_buffer("__SHELL__"),
        make_buffer("__IPYTYON__"),
        make_buffer(TERM_STDOUT),
        make_buffer(TERM_STDERR),
        make_buffer("__idea_chat__"),
        make_buffer("ordinary"),
    ]
    provider = FakeProvider(buffers)
    monkeypatch.setattr("pytoy.shared.ui.pytoy_buffer.PytoyBufferProvider", lambda: provider)
    monkeypatch.setattr(console_command, "_terminate_matching_executions", lambda _: None)

    console_command.hide_buffers("terminal")

    assert provider.closed == [buffer.buffer_id for buffer in buffers[:5]]
