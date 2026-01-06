"""Unit tests for PytoyWindowVim implementation."""
import sys
from pathlib import Path
import pytest
from typing import Generator

from .mocks.vim import MockVim

# Import implementations
from pytoy.ui.pytoy_window.impl_vim import PytoyWindowVim,  PytoyBufferVim

class MockKernelRegistry:
    kernels = {}

    @classmethod
    def get(cls, winid: int):
        if winid not in cls.kernels:
            cls.kernels[winid] = MockKernel(winid)
        return cls.kernels[winid]

    @classmethod
    def dispose(cls, winid: int):
        cls._kernels.pop(winid, None)

class MockKernel:
    def __init__(self, winid):
        self.winid = winid
        self.window = MockWindow()
        self.buffer = MockBuffer()
        self.valid = True

class MockWindow:
    cursor = (1, 0)
    valid = True

class MockBuffer:
    lines = ["Hello world"]


def test_window_creation(vim_env: MockVim):
    """Test window creation and basic properties"""
    buf = vim_env.create_buffer(1, "test.txt")
    win = vim_env.create_window(1, buf)
    pytoy_win = PytoyWindowVim(win, kernel_registry=MockKernelRegistry)
    
    assert isinstance(pytoy_win.buffer.impl, PytoyBufferVim)


