"""Unit tests for PytoyWindowVim implementation."""
import sys
from pathlib import Path
import pytest
from typing import Generator

from .mocks.vim import MockVim

# Import implementations

from pytoy.ui.pytoy_window.impls.vim.kernel import VimWindowKernel
from pytoy.ui.pytoy_window.impls.vim import PytoyWindowVim

class MockKernelRegistry:
    kernels = {}

    @classmethod
    def get(cls, winid: int):
        if winid not in cls.kernels:
            cls.kernels[winid] = MockKernel(winid)
        return cls.kernels[winid]

    @classmethod
    def dispose(cls, winid: int):
        cls.kernels.pop(winid, None)

class MockKernel:
    def __init__(self, winid):
        self.winid = winid
        self.window = MockWindow()
        self.buffer = MockBuffer()
        self.valid = True

class MockWindow:
    cursor = (1, 0)
    valid = True
    winid = 1

class MockBuffer:
    lines = ["Hello world"]
    number = 1


def test_window_creation(vim_env: MockVim):
    """Test window creation and basic properties"""
    buf = vim_env.create_buffer(1, "test.txt")
    win = vim_env.create_window(1, buf)

    kernel_registry = dict()
    kernel_registry[1] = VimWindowKernel(1)
    class DummyCtx():
        @property
        def window_kernel_registry(self):
            return kernel_registry
    pytoy_win = PytoyWindowVim(win.number, ctx=DummyCtx())


