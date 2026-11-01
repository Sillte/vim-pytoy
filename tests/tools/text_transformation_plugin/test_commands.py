from pathlib import Path
from typing import cast

import pytest

from pytoy.commands import text_transformation_commands as commands
from pytoy.commands.text_transformation_commands import ConflictPolicy, _apply_result
from pytoy.shared.ui import PytoyBuffer


class FakeBuffer:
    def __init__(self, content: str, *, valid: bool = True, editable: bool = True) -> None:
        self.content = content
        self.valid = valid
        self.is_normal_type = editable

    def init_buffer(self, content: str) -> None:
        self.content = content


@pytest.mark.parametrize("on_conflict", ["preserve", "overwrite"])
def test_applies_result_when_buffer_is_unchanged(on_conflict: ConflictPolicy) -> None:
    buffer = FakeBuffer("original")
    output: list[str] = []

    _apply_result(cast(PytoyBuffer, buffer), "original", "transformed", on_conflict, output.append)

    assert buffer.content == "transformed"
    assert output == []


def test_preserve_policy_keeps_concurrent_edits_and_shows_result() -> None:
    buffer = FakeBuffer("new edit")
    output: list[str] = []

    _apply_result(cast(PytoyBuffer, buffer), "original", "transformed", "preserve", output.append)

    assert buffer.content == "new edit"
    assert len(output) == 1
    assert "left unchanged" in output[0]
    assert output[0].endswith("transformed")


def test_overwrite_policy_replaces_concurrent_edits() -> None:
    buffer = FakeBuffer("new edit")
    output: list[str] = []

    _apply_result(cast(PytoyBuffer, buffer), "original", "transformed", "overwrite", output.append)

    assert buffer.content == "transformed"
    assert output == []


@pytest.mark.parametrize("buffer", [FakeBuffer("original", valid=False), FakeBuffer("original", editable=False)])
def test_shows_result_when_source_buffer_is_unavailable_or_not_editable(buffer: FakeBuffer) -> None:
    output: list[str] = []

    _apply_result(cast(PytoyBuffer, buffer), "original", "transformed", "overwrite", output.append)

    assert buffer.content == "original"
    assert len(output) == 1
    assert output[0].endswith("transformed")


def test_opens_plugin_folder_with_windows_file_manager(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    opened: list[str] = []
    monkeypatch.setattr(commands.platform, "system", lambda: "Windows")
    monkeypatch.setattr(commands.os, "startfile", opened.append, raising=False)

    commands._open_folder_in_file_manager(tmp_path)

    assert opened == [str(tmp_path)]


def test_opens_plugin_folder_with_linux_file_manager(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    opened: list[list[str]] = []
    monkeypatch.setattr(commands.platform, "system", lambda: "Linux")
    monkeypatch.setattr(commands.subprocess, "Popen", lambda command: opened.append(command))

    commands._open_folder_in_file_manager(tmp_path)

    assert opened == [["xdg-open", str(tmp_path)]]
