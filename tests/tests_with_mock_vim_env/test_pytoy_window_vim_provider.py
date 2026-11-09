from types import SimpleNamespace
from typing import cast

import pytest

from pytoy.shared.lib.text import CursorPosition
from pytoy.shared.ui.contract.buffer.models import BufferSource
from pytoy.shared.ui.contract.window import WindowProtocol
from pytoy.shared.ui.contract.window.models import WindowCreationParam

from .mocks.vim import MockVim


def test_window_open_escapes_target_and_converts_unicode_cursor(vim_env: MockVim, monkeypatch) -> None:
    from pytoy.shared.ui.pytoy_window.impls.vim import PytoyWindowProviderVim, _vim_string_literal

    target = 'folder with space/"quoted"|name\\file.txt'
    eval_calls: list[str] = []
    original_eval = vim_env.eval

    def eval_expression(expression: str):
        eval_calls.append(expression)
        if expression.startswith("bufnr("):
            return "0"
        if expression.startswith("fnameescape("):
            return "escaped-target"
        return original_eval(expression)

    monkeypatch.setattr(vim_env, "eval", eval_expression)
    vim_window = vim_env.current.window
    vim_window.buffer[:] = ["日本語🙂x"]
    anchor = SimpleNamespace(window=vim_window)
    param = WindowCreationParam.for_in_place(anchor=cast(WindowProtocol, anchor), cursor=CursorPosition(0, 3))
    provider = PytoyWindowProviderVim()

    opened = provider._create_window(BufferSource(type="file", name=target), param)

    target_expr = _vim_string_literal(target)
    assert f"bufnr({target_expr})" in eval_calls
    assert f"fnameescape({target_expr})" in eval_calls
    assert "edit escaped-target" in vim_env.get_commands()
    assert opened.cursor == (1, 9)


def test_move_cursor_uses_one_based_line_and_zero_based_byte_column(vim_env: MockVim, monkeypatch) -> None:
    from pytoy.shared.ui.pytoy_window.impls.vim import PytoyWindowVim, _to_vim_coords
    from pytoy.shared.ui.pytoy_window.impls.vim.kernel import VimWindowKernel

    vim_window = vim_env.current.window
    text_buffer = SimpleNamespace(lines=["日本語🙂x"])
    window = PytoyWindowVim.__new__(PytoyWindowVim)
    window._kernel = cast(VimWindowKernel, SimpleNamespace(window=vim_window, winid=1))
    monkeypatch.setattr(PytoyWindowVim, "buffer", property(lambda _: text_buffer))

    window.move_cursor(CursorPosition(0, 3))

    assert _to_vim_coords(text_buffer.lines, CursorPosition(0, 3)) == (1, 10)
    assert vim_window.cursor == (1, 9)


def test_deduplicate_rejects_invalid_scope(vim_env: MockVim) -> None:
    from pytoy.shared.ui.pytoy_window.impls.vim import PytoyWindowVim
    from pytoy.shared.ui.pytoy_window.impls.vim.kernel import VimWindowKernel

    window = PytoyWindowVim.__new__(PytoyWindowVim)
    window._kernel = cast(VimWindowKernel, SimpleNamespace())

    with pytest.raises(ValueError, match="Invalid scope"):
        getattr(window, "deduplicate")("window")
