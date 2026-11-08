from types import SimpleNamespace
from typing import cast

from .mocks.vim import MockVim


def test_temporary_uris_selects_only_untitled_double_underscore_buffers(monkeypatch, vim_env: MockVim):
    from pytoy.shared.ui.vscode.editor import Editor, clearners
    from pytoy.shared.ui.vscode.uri import VSCodeUri

    target = VSCodeUri(scheme="untitled", path="__temporary_output__")
    ordinary_untitled = VSCodeUri(scheme="untitled", path="notes")
    file_buffer = VSCodeUri(scheme="file", path="/__temporary_file__")
    monkeypatch.setattr(
        clearners.BufferURISolver,
        "get_bufnr_to_uris",
        lambda: {1: target, 2: ordinary_untitled, 3: file_buffer},
    )
    cleaner = clearners.EditorCleaner(cast(Editor, SimpleNamespace()))

    assert cleaner.temporary_uris == [target]


def test_close_editors_closes_requested_uris_and_discards_dirty_documents(monkeypatch, vim_env: MockVim):
    from pytoy.shared.ui.vscode.editor import Editor, clearners
    from pytoy.shared.ui.vscode.uri import VSCodeUri

    target = VSCodeUri(scheme="untitled", path="__temporary_output__")
    unrelated = VSCodeUri(scheme="untitled", path="__other_output__")
    calls = []

    class FakeApi:
        def eval_with_return(self, code, *, with_await, opts):
            calls.append((code, with_await, opts))

    monkeypatch.setattr(clearners, "Api", FakeApi)
    cleaner = clearners.EditorCleaner(cast(Editor, SimpleNamespace()))

    result = cleaner.close_editors([target])

    assert result == [target]
    assert len(calls) == 1
    code, with_await, opts = calls[0]
    assert with_await is True
    assert opts["args"]["uriKeys"] == [target.to_key_str()]
    assert unrelated.to_key_str() not in opts["args"]["uriKeys"]
    assert "workbench.action.closeActiveEditor" in code
    assert "workbench.action.revertAndCloseActiveEditor" in code


def test_close_editors_does_not_call_vscode_without_targets(monkeypatch, vim_env: MockVim):
    from pytoy.shared.ui.vscode.editor import Editor, clearners

    def fail_api():
        raise AssertionError("API should not be initialized without target URIs")

    monkeypatch.setattr(clearners, "Api", fail_api)
    cleaner = clearners.EditorCleaner(cast(Editor, SimpleNamespace()))

    assert cleaner.close_editors([]) == []
