"""Base mock implementation of vim module."""
from typing import Any, Dict, List, Optional


class MockVimModule:
    """Base mock implementation of vim module for initial imports."""
    
    class Window:
        """Mock vim.window"""
        def __init__(self):
            self.number = 1
            self.valid = True
            self._buffer = None
        
        @property
        def buffer(self):
            if self._buffer is None:
                self._buffer = MockVimModule.Buffer()
            return self._buffer
    
    class Buffer:
        """Mock vim.buffer"""
        def __init__(self):
            self.number = 1
            self.name = ""
            self.valid = True
            self._content: List[str] = [""]
            self.options: Dict[str, Any] = {
                "buftype": "",
                "swapfile": True
            }
        
        def __getitem__(self, idx):
            return self._content[idx]
        
        def __setitem__(self, idx, value):
            if isinstance(idx, slice):
                if isinstance(value, str):
                    self._content[:] = [value]
                else:
                    self._content[:] = value
            else:
                if isinstance(value, str):
                    self._content[idx] = value
                else:
                    raise TypeError("Cannot assign list to single index")
        
        def append(self, line: str):
            self._content.append(line)
    
    class Current:
        """Mock vim.current"""
        def __init__(self):
            self._window = MockVimModule.Window()
        
        @property
        def window(self):
            return self._window
        
        @property
        def buffer(self):
            return self.window.buffer
    
    def __init__(self):
        self.options: Dict[str, Any] = {"switchbuf": {}}
        self.vars: Dict[str, Any] = {}
        self.windows: List[MockVimModule.Window] = []
        self.buffers: List[MockVimModule.Buffer] = []
        self.current = self.Current()
        self._eval_results: Dict[str, str] = {}
        self._commands: List[str] = []
    
    def command(self, cmd: str) -> None:
        """Mock vim.command"""
        self._commands.append(cmd)
    
    def eval(self, expr: str) -> Any:
        """Mock vim.eval"""
        if expr.startswith("bufwinnr("):
            # Special case for window number lookups
            bufnr = int(''.join(c for c in expr if c.isdigit()))
            for win in self.windows:
                if win.buffer.number == bufnr:
                    return str(win.number)
            return "-1"

        if expr.startswith("bufnr("):
            return 5 
        if expr == "g:lightline":
            return {}
        if expr == "exists('lightline#init')":
            return 0
        if expr == "has('nvim')":
            return 0
        if expr.startswith("win_getid("):
            return 1001
        return self._eval_results.get(expr, "")

    def exec_lua(self, command: str) -> Any:
        return None

    @property
    def lua(self) -> Any:
        from unittest.mock import MagicMock
        mock = MagicMock()
        mock.__call__ = MagicMock(return_value=None) 
        return mock
