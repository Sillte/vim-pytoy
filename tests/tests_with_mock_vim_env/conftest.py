import sys
from collections.abc import Generator

import pytest

from .mocks.vim import MockVim

_vim_mock = MockVim()


# ------------------------------------------------------------
# Runtime support
# ------------------------------------------------------------


@pytest.fixture(autouse=True)
def vim_env() -> Generator[MockVim, None, None]:
    """Provide the mocked Vim module while a Vim-specific test runs."""
    previous_vim = sys.modules.get("vim")

    _vim_mock.reset()
    sys.modules["vim"] = _vim_mock  # type: ignore

    try:
        yield _vim_mock
    finally:
        _vim_mock.reset()

        if previous_vim is None:
            sys.modules.pop("vim", None)
        else:
            sys.modules["vim"] = previous_vim
