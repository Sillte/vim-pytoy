from pathlib import Path
from pytoy.tools.pytest.utils.script_decipher import ScriptDecipher  # NOQA
from pytoy.tools.pytest.utils.pytest_decipher import PytestDecipher  # NOQA

def to_func_command(path: str | Path, line: int, suffix: str = "") -> str:
    """Return the executable `pytest` command.
    """
    instance = ScriptDecipher.from_path(Path(path))
    target = instance.pick(line)
    if not target:
        raise ValueError(
            "Specified `path` and `line` is invalid in `PytestExecutor`."
        )
    return f"{target.command} {suffix}"
