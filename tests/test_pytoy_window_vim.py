"""Unit tests for PytoyWindowVim implementation."""
import sys
from pathlib import Path
import pytest
from typing import Generator

from .mocks.vim import MockVim

# Import implementations
from pytoy.ui.pytoy_window.impl_vim import PytoyWindowVim,  PytoyBufferVim


def test_window_creation(vim_env: MockVim):
    """Test window creation and basic properties"""
    buf = vim_env.create_buffer(1, "test.txt")
    win = vim_env.create_window(1, buf)
    pytoy_win = PytoyWindowVim(win)
    
    assert isinstance(pytoy_win.buffer.impl, PytoyBufferVim)


