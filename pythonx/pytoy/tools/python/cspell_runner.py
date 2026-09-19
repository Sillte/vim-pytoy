from pathlib import Path

from pytoy.shared.ui.pytoy_quickfix import Quickfix, QuickfixRecordsCreator
from pytoy.tools.cspell import CSpellOneFileChecker


class CSpellRunner:
    def __init__(self):
        pass

    def run(self) -> None:
        from pytoy.shared.ui import PytoyBuffer

        path = PytoyBuffer.get_current().file_path

        if Path(path).suffix == ".py":
            checker = CSpellOneFileChecker(only_python_string=True)
        else:
            checker = CSpellOneFileChecker(only_python_string=False)
        output = checker(path)
        regex = r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+).*\((?P<text>(.+))\)"
        records = QuickfixRecordsCreator.from_regex(regex).create(output, path.parent)
        Quickfix.from_any(records, try_reuse=True, working_directory=path.parent)
