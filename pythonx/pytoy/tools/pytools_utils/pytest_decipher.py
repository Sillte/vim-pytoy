import re
from typing import Dict, List

from collections import defaultdict


class PytestDecipher:
    """Interpret `stdout` /`stderr` of pytest, and contruct
    QuickList's information.


    Observation Note
    -----------------

    * `pytest` reports has some sections and ~======` is sepearator.
    * Each section has multiple `items` and `separators`~ are `-`.
    * Each item is `ERROR` or `FAILURE`.
    * The path and line are described in one line.
    * For 1 `ERROR` or `FAILURE` multiple `positions` correspond.
        - This is because stack of exceptions may be described.

    """

    # Definition `Section`.
    _SEPARATORS = dict()
    _SEPARATORS["START"] = re.compile(r"^=+ test session starts =+$")
    _SEPARATORS["ERRORS"] = re.compile(r"^=+ ERRORS =+$")
    _SEPARATORS["FAILURES"] = re.compile(r"^=+ FAILURES =+$")
    _SEPARATORS["END"] = re.compile(r"^=+ short test summary info =+$")

    def __init__(self, text: str):
        records: List[Dict] = []
        sections = self._to_sections(text)
        error_items = self._to_items(sections["ERRORS"])
        failure_items = self._to_items(sections["FAILURES"])
        for item_text in error_items.values():
            records += self._to_records(item_text)
        for item_text in failure_items.values():
            records += self._to_records(item_text)
        self.records = records

    def _to_sections(self, text: str) -> Dict[str, str]:
        """Separate `each` sections."""
        section_to_lines = {key: [] for key in self._SEPARATORS}
        lines = text.split("\n")
        current = None
        for line in lines:
            for key, pattern in self._SEPARATORS.items():
                if pattern.match(line):
                    current = key
            if current:
                section_to_lines[current].append(line)
        section_to_text = {
            key: "\n".join(value) for key, value in section_to_lines.items()
        }
        return section_to_text

    def _to_items(self, section_text: str) -> Dict[str, str]:
        """Separate to `each` items.

        Return:
            `dict`: (item-name) -> (text)

        """
        # `item`'s separator.
        item_separator = re.compile(r"^_+\s(.+)\s_+$")

        item_to_lines = defaultdict(list)
        item = None
        for line in section_text.split("\n"):
            if m := item_separator.match(line):
                item = m.group(1)
            if item is not None:
                item_to_lines[item].append(line)
        return {item: "\n".join(lines) for item, lines in item_to_lines.items()}

    def _to_records(self, item_text: str) -> List[Dict]:
        """Convert text of item to `list` of `dict`.
        Each `dict` of `list` is valid for `vim's `quicklist`.
        """
        lines = item_text.split("\n")
        detail_specifier = re.compile(r"^E\s*(?P<reason>.+)$")

        # As for `filename`, 2 pattern exist.
        summary_specifier = re.compile(
            r"(?P<filename>(.*)\.py):(?P<lnum>\d+)(:(?P<text>.*))?$"
        )
        summary_specifier2 = re.compile(
            r'^E\s*File\s*"(?P<filename>.*)",\s*line\s*(?P<lnum>\d+)\s*$'
        )
        summaries = []
        details = []
        for line in lines:
            m = summary_specifier.match(line)
            if m:
                summaries.append(m)
                continue
            m = summary_specifier2.match(line)
            if m:
                summaries.append(m)
                continue

            m = detail_specifier.match(line)
            if m:
                details.append(m)
        if not summaries:
            return [{"filename": "BUG?", "lnum": 1, "text": item_text}]
        records = []
        for summary in summaries:
            row = summary.groupdict()
            row["lnum"] = int(row["lnum"])
            if "text" not in row:
                row["text"] = "No Text"
            records.append(row)
        if details:
            records[-1]["text"] = " ".join(elem.group("reason") for elem in details)
        return records


if __name__ == "__main__":
    # makeshift test.
    #import subprocess
    #from subprocess import PIPE

    # proc = subprocess.run("pytest", stdout=PIPE, shell=True, text=True)
    # instance = PytestDecipher(proc.stdout)

    TEXT = r"""============================= test session starts =====================
platform win32 -- Python 3.8.2, pytest-6.2.1, py-1.10.0, pluggy-0.13.1
ootdir: C:\Users\sillte\Desktop\JupyterReadering\pytest_reading
plugins: anyio-2.2.0, cov-2.8.1
collected 0 items / 1 error

=================================== ERRORS ===================================
________________________ ERROR collecting test_hoge.py _______________________
test_hoge.py:4: in <module>
hogegheoge
E   NameError: name 'hogegheoge' is not defined
=========================== short test summary info ===========================
ERROR test_hoge.py - NameError: name 'hogegheoge' is not defined
============================== 1 error in 0.16s ===============================
    """
    instance = PytestDecipher(TEXT)
    print(instance.records)
