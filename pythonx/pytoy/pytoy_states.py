"""In this subpackage, the configuration of   

"""

from enum import Enum


class ExecutionMode(Enum):
    """Specify the (intended) execution mode
    of the script for `python` and `pytest`.

    NOTE: Some tools such as `black` or `ruff` are more desirable to execute the isolated
    environment, hence, this execution mode is only applicable in `python` and `pytest`.
    """

    NAIVE: str = "NAIVE"
    VENV: str = "VENV"
    WITH_UV: str = "WITH_UV"  # Use


class _ExecutionModeManager:

    mode = ExecutionMode.NAIVE

    @classmethod
    def get_mode(cls):
        return cls.mode

    @classmethod
    def set_mode(cls, mode: ExecutionMode):
        cls.mode = mode


_DEFAULT_EXECUTION_MODE = ExecutionMode.NAIVE


def get_default_execution_mode():
    return _ExecutionModeManager.get_mode()


def set_default_execution_mode(mode: ExecutionMode):
    _ExecutionModeManager.set_mode(mode)


if __name__ == "__main__":
    set_default_execution_mode(ExecutionMode.WITH_UV)
    assert get_default_execution_mode() == ExecutionMode.WITH_UV
