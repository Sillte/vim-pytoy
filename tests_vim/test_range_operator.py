# Please execute this with `:PytoyExecute`

# (replace_text): 
# It is very low risk that the difference of `start` changes problem 
from pytoy.ui.pytoy_window import PytoyWindowProvider, WindowCreationParam
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.infra.core.models import CursorPosition, CharacterRange
from pathlib import Path

import vim

# Tests for `range_operator.replace_text`. 

def _get_buffer(text: str | None = None) -> PytoyBuffer:
    param = WindowCreationParam.for_split("vertical", try_reuse=True)
    window = PytoyWindowProvider().open_window("hoge", param)
    if text is not None:
        buffer = window.buffer
        operator = window.buffer.range_operator
        entire = operator.entire_character_range
        operator.replace_text(entire, text)
        assert buffer.content == text , ("`entire-replace`", buffer.content, text, entire)
    return window.buffer

def test_intersetion_case():
    target_texts_normal = ["SingleLine", "Multi\nLine"]
    target_texts_edge = ["", "\n", "\n\n", "\nhello, \nworld\n"]

    buffer = _get_buffer("")
    operator = buffer.range_operator
    for target_text in [*target_texts_normal, *target_texts_edge]:
        s  = CursorPosition(0, 0)
        t  = CursorPosition(0, 0)
        cr = CharacterRange(s, t)
        cr = operator.replace_text(cr, target_text)
        assert cr, "cr is not empty"
        text = operator.get_text(cr)
        assert target_text == text, (target_text, text, cr)
    print("All pass for insertion case.")

test_intersetion_case()


def test_complete_replace_case():
    target_texts_normal = ["SingleLine", "Multi\nLine"]
    target_texts_edge = ["", "\n", "\n\n", "\nhello, \nworld\n"]

    param = WindowCreationParam.for_split("vertical", try_reuse=True)
    window = PytoyWindowProvider().open_window("hoge", param)
    buffer = _get_buffer()
    operator = buffer.range_operator
    for target_text in [*target_texts_normal, *target_texts_edge]:
        cr = operator.entire_character_range
        cr = window.buffer.range_operator.replace_text(cr, target_text)
        text = operator.get_text(cr)
        assert target_text == text,  target_text
    print("All pass for complete replace case.")

test_complete_replace_case()

def test_insert_multiline_into_empty_range():
    buffer = _get_buffer("AAA\nBBB\nCC\n")
    op = buffer.range_operator
    cr = CharacterRange(CursorPosition(1,1), CursorPosition(1,1))
    new = op.replace_text(cr, "X\nY")
    assert op.get_text(new) == "X\nY"
    actual = op.get_text(op.entire_character_range)
    assert actual == "AAA\nBX\nYBB\nCC\n", (actual, buffer.lines, op.entire_character_range)

    print("Pass for test_insert_multiline_into_empty_range")

test_insert_multiline_into_empty_range()

def test_multiline_replace_single_line():
    buffer = _get_buffer("AAA\nBBB\nCCC")
    op = buffer.range_operator
    cr = CharacterRange(CursorPosition(0,1), CursorPosition(2,2))
    new = op.replace_text(cr, "X")
    assert op.get_text(new) == "X"
    actual = op.get_text(op.entire_character_range)
    assert actual == "AXC", (actual, )
    print("Pass for test_multiline_replace_single_line")

test_multiline_replace_single_line()


def test_idempotent_replace():
    param = WindowCreationParam.for_split("vertical", try_reuse=True)
    window = PytoyWindowProvider().open_window("hoge", param)
    operator = window.buffer.range_operator

    texts = ["abc", "a\nb\nc", "", "\n", "\n\nxyz\n"]

    for text in texts:
        cr = CharacterRange(CursorPosition(0, 0), CursorPosition(0, 0))
        cr1 = operator.replace_text(cr, text)
        cr2 = operator.replace_text(cr1, text)
        assert operator.get_text(cr2) == text
    print("Idempotent replace passed.")

test_idempotent_replace()


def test_multiline_boundary_replace_multiline():
    buffer = _get_buffer("AAA\nBBB\nCCC")
    op = buffer.range_operator
    cr = CharacterRange(CursorPosition(1,0), CursorPosition(2,0))
    new = op.replace_text(cr, "X\nY")
    assert op.get_text(new) == "X\nY"
    assert op.get_text(op.entire_character_range) == "AAA\nX\nY\nCCC"
    print("Pass for test_multiline_boundary_replace_multiple")

test_multiline_boundary_replace_multiline()

