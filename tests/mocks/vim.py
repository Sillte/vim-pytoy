"""Mock implementation of vim module for testing."""
from typing import Any, Dict, List, Optional
from pathlib import Path
from .vim_base import MockVimModule


class MockVim(MockVimModule):
    """Enhanced mock implementation of vim module for testing."""
    
    def __init__(self):
        super().__init__()
        self.reset()
    
    def reset(self):
        """Reset all state to defaults."""
        self.options = {}
        self.vars = {}
        self.windows = []
        self.buffers = []
        self._eval_results = {}
        self._commands = []
        self.current = self.Current()
    
    def create_buffer(self, number: int, name: str = "", content: Optional[List[str]] = None) -> MockVimModule.Buffer:
        """Create a new buffer for testing."""
        buf = self.Buffer()
        buf.number = number
        buf.name = name
        if content:
            buf[:] = content
        self.buffers.append(buf)
        return buf
    
    def create_window(self, number: int, buffer: MockVimModule.Buffer) -> MockVimModule.Window:
        """Create a new window for testing."""
        win = self.Window()
        win.number = number
        win._buffer = buffer
        self.windows.append(win)
        if not self.current.window:
            self.current._window = win
        return win
    
    def set_current_window(self, window: MockVimModule.Window):
        """Set the current window."""
        if window in self.windows:
            self.current._window = window
    
    def set_eval_result(self, expr: str, result: Any):
        """Set a result for vim.eval()."""
        self._eval_results[expr] = result
    
    @property
    def last_command(self) -> Optional[str]:
        """Get the last command executed."""
        return self._commands[-1] if self._commands else None
    
    def get_commands(self) -> List[str]:
        """Get all commands executed."""
        return self._commands.copy()