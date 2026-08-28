"""Unit tests for PytoyWindowVim implementation."""

# Import implementations
from pytoy.shared.ui.pytoy_window.impls.vim.kernel import VimWindowKernel

from .mocks.vim import MockVim


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

    kernel_registry = dict()
    kernel_registry[1] = VimWindowKernel(1)
