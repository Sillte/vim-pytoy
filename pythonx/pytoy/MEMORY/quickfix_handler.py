"""Perform operations related to `Quickfix`. 
"""
import os

from pytoy.ui_utils import QuickFix
from pytoy.git_utils.git_user import GitUser
from pathlib import Path

import vim


class QuickFixFilter:
    """Filter `QuickFix`'s contents based on `context`."""

    def __init__(self, location=None):
        self.location = location

    def restrict_on_git(self, cwd=None):
        if cwd is None:
            pass
        path = Path(vim.current.buffer.name)
        if path.is_dir():
            cwd = path
        else:
            cwd = path.parent
        user = GitUser(cwd)
        paths = user.target_files
        target_folders = set(path.parent for path in user.target_files)

        def _predicate(record):
            if "filename" not in record:
                return False
            if Path(record["filename"]).parent in target_folders:
                return True
            return False

        self._from_predicate(_predicate)

    def _from_predicate(self, predicate):
        """Apply the `filter` based on the `predicate`.
        Here, the signature of `predicate` (record) -> bool.
        """

        def _filter(fix: QuickFix):
            records = fix.read()
            records = [record for record in records if predicate(record)]
            fix.write(records)

        fix = QuickFix(location=self.location)
        _filter(fix)


class QuickFixSorter:
    """Sort `QuickFix` based on criteria."""

    def __init__(self, location=None):
        self.location = location

    def sort_by_time(self):
        """Sort following to the modified time."""

        def _key_func(record):
            path = Path(record["filename"])
            try:
                if not path.exists():
                    return 0
            except:
                return 0
            return os.path.getmtime(path)

        self._from_key(_key_func, reverse=True)

    def _from_key(self, key, reverse=False):
        """Apply `sort` from key function of `sorted`."""

        def _inner(fix: QuickFix):
            records = fix.read()
            records = sorted(records, key=key, reverse=reverse)
            fix.write(records)

        fix = QuickFix(location=self.location)
        _inner(fix)
