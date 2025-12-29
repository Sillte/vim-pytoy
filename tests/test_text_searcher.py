from pytoy.infra.core.models import CursorPosition, CharacterRange
from pytoy.ui.pytoy_buffer.text_searchers import TextSearcher

def test_find_first_single_line():
    lines = ["hello world"]
    searcher = TextSearcher.create(lines)

    result = searcher.find_first("world")

    assert result is not None
    assert result.start == CursorPosition(0, 6)
    assert result.end == CursorPosition(0, 11)

def test_find_first_multi_line():
    lines = [
        "firstline", 
        "hello",
        "AA beautiful world",
    ]
    searcher = TextSearcher.create(lines)

    result = searcher.find_first("beautiful")

    assert result is not None
    assert result.start == CursorPosition(2, 3)
    assert result.end == CursorPosition(2, 12)
    

def test_find_all_multiple_matches():
    lines = ["abc abc abc"]
    searcher = TextSearcher.create(lines)

    results = searcher.find_all("abc")

    assert len(results) == 3
    assert results[0].start == CursorPosition(0, 0)
    assert results[1].start == CursorPosition(0, 4)
    assert results[2].start == CursorPosition(0, 8)


def test_find_within_character_range_single_line():
    lines = ["aaa bbb ccc"]
    target_range = CharacterRange(
        start=CursorPosition(0, 4),
        end=CursorPosition(0, 11),
    )

    searcher = TextSearcher.create(lines, target_range)
    result = searcher.find_first("bbb")

    assert result is not None
    assert result.start == CursorPosition(0, 4)
    assert result.end == CursorPosition(0, 7)

def test_find_within_character_range_multi_line():
    lines = [
        "aaa",
        "bbb",
        "ccc",
    ]
    target_range = CharacterRange(
        start=CursorPosition(0, 1),
        end=CursorPosition(2, 2),
    )

    searcher = TextSearcher.create(lines, target_range)
    result = searcher.find_first("bbb")

    assert result is not None
    assert result.start == CursorPosition(1, 0)
    assert result.end == CursorPosition(1, 3)

def test_find_first_not_found():
    lines = ["hello world"]
    searcher = TextSearcher.create(lines)

    result = searcher.find_first("xyz")

    assert result is None

def test_find_empty_text():
    lines = ["abc"]
    searcher = TextSearcher.create(lines)

    assert searcher.find_first("") is None
    assert searcher.find_all("") == []

def test_find_first_reverse():
    lines = ["abc abc abc"]
    searcher = TextSearcher.create(lines)

    result = searcher.find_first("abc", reverse=True)

    assert result is not None
    assert result.start == CursorPosition(0, 8)