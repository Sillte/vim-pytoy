"""Test configuration and shared fixtures for vim-pytoy tests."""
import sys
from typing import Generator
import pytest


# Import mock implementations using relative imports
from .mocks.vim import MockVim

# Initialize mock instances
_vim_mock = MockVim()

# Ensure vim module is available for imports
if 'vim' not in sys.modules:
    sys.modules['vim'] = _vim_mock

@pytest.fixture(autouse=True)
def vim_mock() -> Generator[MockVim, None, None]:
    """Provide mock vim environment for tests.
    
    Yields:
        vim_mock_module.MockVim: A fresh mock vim environment
    """
    old_vim = sys.modules.get('vim')
    _vim_mock.reset()
    sys.modules['vim'] = _vim_mock
    
    try:
        yield _vim_mock
    finally:
        if old_vim is not None:
            sys.modules['vim'] = old_vim

@pytest.fixture(autouse=True)
def vim_env() -> Generator[MockVim, None, None]:
    """Provide mock vim environment for all tests."""
    old_vim = sys.modules['vim']
    sys.modules['vim'] = _vim_mock
    _vim_mock.reset()
    yield _vim_mock
    sys.modules['vim'] = old_vim


