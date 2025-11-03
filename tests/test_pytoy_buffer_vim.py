"""Unit tests for PytoyBufferVim implementation."""
import sys
from pathlib import Path
import pytest
from typing import Generator


# Now we can import our actual implementation
from pytoy.ui.pytoy_buffer.impl_vim import PytoyBufferVim

from tests.mocks.vim import MockVim



def test_buffer_init(vim_env: MockVim):
    """Test buffer initialization and content setting"""
    # Setup
    buf = vim_env.create_buffer(1, "test.txt")
    pytoy_buf = PytoyBufferVim(buf)
    
    # Test empty init
    pytoy_buf.init_buffer()
    assert buf._content == [""]
    
    # Test with content
    test_content = "line1\r\nline2\nline3"
    pytoy_buf.init_buffer(test_content)
    assert buf._content == ["line1", "line2", "line3"]



def test_buffer_valid(vim_env: MockVim):
    """Test valid property"""
    # Valid buffer
    buf = vim_env.create_buffer(1, "test.txt")
    buf.valid = True
    pytoy_buf = PytoyBufferVim(buf)
    assert pytoy_buf.valid == True
    
    # Invalid buffer
    buf.valid = False
    assert pytoy_buf.valid == False


def test_get_current(vim_env: MockVim):
    """Test get_current class method"""
    buf = vim_env.create_buffer(1, "test.txt")
    win = vim_env.create_window(1, buf)
    vim_env.set_current_window(win)
    
    current_buf = PytoyBufferVim.get_current()
    assert isinstance(current_buf, PytoyBufferVim)
