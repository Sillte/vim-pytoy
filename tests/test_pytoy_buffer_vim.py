"""Unit tests for PytoyBufferVim implementation."""
import sys
from pathlib import Path
import pytest
from typing import Generator


# Now we can import our actual implementation
from pytoy.ui.pytoy_buffer.impls.vim import PytoyBufferVim, VimBufferKernel

from tests.mocks.vim import MockVim



def test_buffer_init(vim_env: MockVim):
    """Test buffer initialization and content setting"""
    # Setup
    buf = vim_env.create_buffer(1, "test.txt")
    kernel_registry = dict()
    kernel_registry[1] = VimBufferKernel(1)
    assert  kernel_registry.get(1)
    class DummyCtx:
        @property
        def buffer_kernel_registry(self):
            return kernel_registry

    pytoy_buf = PytoyBufferVim(buf.number, ctx=DummyCtx())
    assert pytoy_buf._kernel is not None

    
    # Test empty init
    pytoy_buf.init_buffer()
    assert buf._content == [""]
    
    # Test with content
    test_content = "line1\r\nline2\nline3"
    pytoy_buf.init_buffer(test_content)
    assert buf._content == ["line1", "line2", "line3"]



def test_buffer_valid(vim_env: MockVim):
    """Test valid property"""
    # Setup kernel registry
    kernel_registry = dict()
    
    # Create buffer first
    buf = vim_env.create_buffer(1, "test.txt")
    buf.valid = True
    
    # Create kernel that will retrieve the buffer from vim_env
    kernel = VimBufferKernel(1)
    kernel_registry[1] = kernel

    class DummyCtx:
        @property
        def buffer_kernel_registry(self):
            return kernel_registry
    
    pytoy_buf = PytoyBufferVim(buf.number, ctx=DummyCtx())
    assert pytoy_buf.valid == True
    
    # Test invalid buffer by making it invalid
    buf.valid = False
    assert pytoy_buf.valid == False


def test_get_current(vim_env: MockVim):
    """Test get_current class method"""
    # Setup kernel registry
    
    
    # Setup buffer and window
    buf = vim_env.create_buffer(1, "test.txt")
    win = vim_env.create_window(1, buf)
    vim_env.set_current_window(win)
    
    # Set the buffer in kernel
    kernel_registry = dict()
    kernel_registry[1] = VimBufferKernel(1)
    kernel_registry[1]._buffer = buf
    
    
    current_buf = PytoyBufferVim.get_current()
    assert isinstance(current_buf, PytoyBufferVim)

