"""Unit tests for PytoyBufferVim implementation."""

# Now we can import our actual implementation

from .mocks.vim import MockVim


def test_buffer_init(vim_env: MockVim):
    """Test buffer initialization and content setting"""
    from pytoy.shared.ui.pytoy_buffer.impls.vim import PytoyBufferVim, VimBufferKernel

    # Setup
    buf = vim_env.create_buffer(1, "test.txt")
    kernel_registry = dict()
    kernel_registry[1] = VimBufferKernel(1)
    assert kernel_registry.get(1)

    class DummyCtx:
        @property
        def buffer_kernel_registry(self):
            return kernel_registry

    pytoy_buf = PytoyBufferVim(buf.number, ctx=DummyCtx())  # type: ignore
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
    from pytoy.shared.ui.pytoy_buffer.impls.vim import PytoyBufferVim, VimBufferKernel

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

    pytoy_buf = PytoyBufferVim(buf.number, ctx=DummyCtx())  # type: ignore
    assert pytoy_buf.valid

    # Test invalid buffer by making it invalid
    buf.valid = False
    assert not pytoy_buf.valid
