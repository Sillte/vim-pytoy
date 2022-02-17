"""Perform operations related to `Quickfix`. 
"""

from pytoy.ui_utils import QuickFix
from pytoy.git_utils.git_user import GitUser
from pathlib import Path

import vim


class QuickFixFilter:
    """Filter `QuickFix`'s contents based on `context`."""

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

        # In default, this is applied to both of `location-window` and `quick-fix window`.
        loc_fix = QuickFix(location=True)
        records = loc_fix.read()
        records = [record for record in records if _predicate(record)]
        loc_fix.write(records)

        win_fix = QuickFix(location=False)
        records = loc_fix.read()
        records = [record for record in records if _predicate(record)]
        win_fix.write(records)


class QuickFixSorter:
    """Not yet implemented."""

    def __init__(self):
        pass
