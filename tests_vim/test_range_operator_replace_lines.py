# Please execute this with `:PytoyExecute`
from pytoy.ui.pytoy_window import PytoyWindowProvider, WindowCreationParam
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.infra.core.models import CursorPosition, LineRange
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

def test_insertion_case():
    simple_lines = ["FirstLine", "SecondLine"]
    buffer = _get_buffer("")
    operator = buffer.range_operator
    lr = LineRange(0, 0)
    lr = operator.replace_lines(lr, simple_lines)
    actual = operator.get_lines(lr)
    assert simple_lines == operator.get_lines(lr), (actual, simple_lines, lr)

    print("All pass for insertion case.")
    
test_insertion_case() 

def test_replace_case():
    simple_lines = ["FirstLine", "SecondLine"]
    buffer = _get_buffer("Line0\nLine1")
    operator = buffer.range_operator
    lr = LineRange(0, 1)
    lr = operator.replace_lines(lr, simple_lines)
    actual = operator.get_lines(lr)
    entire_expected =  [*simple_lines, "Line1"]

    assert simple_lines == operator.get_lines(lr), (actual, simple_lines, lr)
    assert entire_expected == buffer.lines

    print("All pass for replace case.")

test_replace_case() 