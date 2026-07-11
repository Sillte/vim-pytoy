from pytoy.shared.ui import PytoyQuickfix
from pytoy.shared.ui.pytoy_quickfix import to_quickfix_creator
from pytoy.tools.cspell import CSpellOneFileChecker


from pathlib import Path


class CSpellRunner:
    def __init__(self):
        pass

    def run(self) -> None:
        from pytoy import TERM_STDOUT
        from pytoy.shared.ui import PytoyBuffer

        path = PytoyBuffer.get_current().file_path

        if Path(path).suffix == ".py":
            checker = CSpellOneFileChecker(only_python_string=True)
        else:
            checker = CSpellOneFileChecker(only_python_string=False)
        output = checker(path)
        regex = r"(?P<filename>.+):(?P<lnum>\d+):(?P<col>\d+).*\((?P<text>(.+))\)"
        maker = to_quickfix_creator(regex)
        records = maker(output, path.parent)
        PytoyQuickfix().handle_records(records)
