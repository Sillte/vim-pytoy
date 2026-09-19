from pathlib import Path

from pytoy.shared.ui.pytoy_quickfix import QuickfixRecord, QuickfixRecordsCreator


def test_records_creator_from_regex_builds_records_with_working_directory() -> None:
    creator = QuickfixRecordsCreator.from_regex(r"(?P<filename>[^:]+):(?P<lnum>\d+):(?P<text>.*)")

    records = creator("main.py:3:syntax error\nignored", Path("/workspace"))

    assert records == [
        QuickfixRecord(filename=str(Path("/workspace/main.py")), lnum=3, text="syntax error"),
    ]


def test_records_creator_normalizes_single_record_from_callable() -> None:
    record = QuickfixRecord(filename="main.py", lnum=3, text="syntax error")
    creator = QuickfixRecordsCreator.from_any(lambda content, working_directory: record)

    assert creator("output", Path("/workspace")) == [record]
