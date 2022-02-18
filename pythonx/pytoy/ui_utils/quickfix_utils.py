from typing import Optional, Any, List, Dict
from pathlib import Path
from pytoy.ui_utils._converter import to_window_id
import vim

class QuickFix: 
    """Handling `quickfix` and `locationlist`

    Args:
        location: If `None`, it accesses `quickfix`.
                  Otherwise, it is regarded as `window`. 
    Note
    -----
    """

    v_getqflist = vim.Function("getqflist")
    v_setqflist = vim.Function("setqflist")

    v_getloclist = vim.bindeval('function("getloclist")')
    v_setloclist = vim.bindeval('function("setloclist")')

    def __init__(self, location=None):
        if location is False:
            location = None
        elif location is True:
            location = vim.current.window

        if location is not None:
            location = to_window_id(location)
        self.location: Optional[int] = location

    def write(self, records: List[Dict[str, Any]]):
        if self.location is None:
            self.v_setqflist(records)
        else:
            self.v_setloclist(self.location, records,)

    def read(self) -> List[Dict[str, Any]]:
        if self.location is None:
            items = self.v_getqflist()
        else:
            items = self.v_getloclist(self.location)
        def _convert(item):
            def _inner(arg):
                if isinstance(arg, bytes):
                    return arg.decode()
                return arg
            # `bytes` keys are returned, so revised. 
            return {_inner(key): _inner(value) for key, value in item.items()}
        records = [_convert(item) for item in items]
        for record in records:
            record["filename"] = vim.buffers[record["bufnr"]].name
        return records


def perform_sample(location=None):
    """Sample usage for `QuickFix`.  
    """
    quickfix = QuickFix(location=location)
    _this_folder = Path(__file__).absolute().parent
    records = []
    for path in _this_folder.glob("*.py"):
        record = dict()
        record["filename"] = str(path)
        record["lnum"] = 1
        record["text"] = str(path.name)
        records.append(record)
    quickfix.write(records)

    return quickfix.read()





